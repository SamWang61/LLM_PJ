"""Replace confidential blob revisions with independently verified ciphertext.

Preserves the Drive file ID, name and parents. Every old version is downloaded,
encrypted, independently downloaded/decrypted and pinned before its plaintext
revision can be removed. No ACL restoration; recovery state stays private.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from drive_backup_acl import identifier, write_private_json, DriveError
from drive_backup_isolation import owner_only, INLINE_FIELDS
from drive_backup_payload import hashes
from drive_backup_transfer import download, upload, readback, matches
from encrypted_backup import encrypt, decrypt, MAGIC

REV_FIELDS = 'id,mimeType,modifiedTime,keepForever,md5Checksum,size,originalFilename'


def revisions(drive, file_id):
    return list(drive.pages(f'files/{identifier(file_id)}/revisions', 'revisions', pageSize=1000,
                           fields=f'nextPageToken,revisions({REV_FIELDS})'))


def pin(drive, file_id, revision_id):
    path = f'files/{identifier(file_id)}/revisions/{identifier(revision_id)}'
    for attempt in range(3):
        row = drive.request('GET', path, params={'fields': REV_FIELDS})
        if row.get('id') != revision_id: raise DriveError('Revision identity mismatch')
        if row.get('keepForever') is True: return row
        # Only a verified false state can retry this idempotent metadata setting.
        try:
            drive.request('PATCH', path, params={'fields': REV_FIELDS}, json={'keepForever': True})
        except Exception:
            pass
        row = drive.request('GET', path, params={'fields': REV_FIELDS})
        if row.get('id') == revision_id and row.get('keepForever') is True: return row
        if attempt < 2: time.sleep(2 ** attempt)
    raise DriveError('Revision preservation was not verified')


def verify_cipher_recovery(drive, file_id, revision_id, record, directory, key):
    ciphertext = directory / ('cloud-' + revision_id)
    download(drive, file_id, ciphertext, record['ciphertext'], revision=revision_id)
    restored = directory / ('recovered-' + revision_id)
    if restored.exists():
        actual, _ = hashes(restored)
        if actual != record['plaintext']: raise DriveError('Existing restored copy differs')
    else:
        decrypt(ciphertext, restored, key)
        actual, _ = hashes(restored)
        if actual != record['plaintext']: raise DriveError('Cloud authenticated recovery differs')
    return {'authenticated': True, 'cloud_revision': revision_id,
            'plaintext_sha256': actual['sha256'], 'checked_at': datetime.now(timezone.utc).isoformat()}


def purge_preserved_plaintext(drive, file_id, row):
    """Only exact private journal entries with authenticated cloud recovery qualify."""
    proof = row.get('recovery', {})
    old, new = row.get('original_revision'), row.get('encrypted_revision')
    if (not old or not new or old == new or proof.get('authenticated') is not True
            or proof.get('cloud_revision') != new
            or proof.get('plaintext_sha256') != row.get('plaintext', {}).get('sha256')):
        raise ValueError('No authenticated encrypted replacement; plaintext cannot be removed')
    current = readback(drive, file_id)
    if current.get('headRevisionId') == old:
        raise ValueError('Original plaintext is still the head revision')
    old_rows = revisions(drive, file_id)
    if new not in {r['id'] for r in old_rows}:
        raise ValueError('Encrypted replacement revision no longer exists')
    if old in {r['id'] for r in old_rows}:
        try:
            drive.request('DELETE', f'files/{identifier(file_id)}/revisions/{identifier(old)}')
        except Exception:
            pass
        if old in {r['id'] for r in revisions(drive, file_id)}:
            raise DriveError('Plaintext revision removal not verified')
    return True


def remediate_file(drive, file_id, directory, key):
    """Resume only from this file's saved journal; never manufacture missing proof."""
    file_id = identifier(file_id)
    directory, key = Path(directory).resolve(), Path(key).resolve()
    if key.is_relative_to(directory): raise ValueError('Key must be outside remediation output')
    directory.mkdir(parents=True, exist_ok=True)
    journal = directory / 'journal.json'
    current_acl = drive.request('GET', f'files/{file_id}', params={'fields': INLINE_FIELDS})
    owner_only(current_acl)
    if current_acl['mimeType'].startswith('application/vnd.google-apps.'):
        raise ValueError('Native documents need a separate remediation policy')
    if journal.exists():
        state = json.loads(journal.read_text(encoding='utf8'))
        if state['file_id'] != file_id: raise ValueError('Wrong remediation journal')
    else:
        original = readback(drive, file_id)
        versions = revisions(drive, file_id)
        if not versions or original['headRevisionId'] not in {r['id'] for r in versions}:
            raise ValueError('Revision inventory does not include the current head')
        versions.sort(key=lambda row: (row['id'] == original['headRevisionId'], row.get('modifiedTime', ''), row['id']))
        state = {'file_id': file_id, 'original': original, 'versions': versions,
                 'records': {}, 'complete': False, 'started_at': datetime.now(timezone.utc).isoformat()}
        write_private_json(journal, state)
    original = state['original']
    for version in state['versions']:
        revision_id = identifier(version['id'])
        row = state['records'].setdefault(revision_id, {'original_revision': revision_id})
        if row.get('plaintext_removed'): continue
        if not row.get('encrypted_revision'):
            pin(drive, file_id, revision_id)
            expected = {'size': int(version['size']), 'md5': version['md5Checksum']}
            plain = directory / ('original-' + revision_id)
            plain_hash = download(drive, file_id, plain, expected, revision=revision_id)
            with plain.open('rb') as stream:
                if stream.read(len(MAGIC)) == MAGIC:
                    raise ValueError('Existing encrypted revision requires validated earlier manifest')
            cipher = directory / ('encrypted-' + revision_id)
            if not cipher.exists(): encrypt(plain, cipher, key)
            cipher_hash, _ = hashes(cipher)
            row.update(plaintext=plain_hash, ciphertext=cipher_hash, phase='upload_requested')
            write_private_json(journal, state)
            current = readback(drive, file_id)
            for field in ('name','parents'):
                if current.get(field) != original.get(field): raise DriveError('File identity changed')
            metadata = {'mimeType': 'application/octet-stream', 'appProperties': {
                **current.get('appProperties', {}), 'llmBackupEncrypted': 'v1',
                'llmBackupPlainSHA256': plain_hash['sha256']}}
            uploaded = current if matches(current, cipher_hash) else upload(drive, cipher, file_id, metadata, cipher_hash)
            row['encrypted_revision'] = uploaded['headRevisionId']
            row['phase'] = 'ciphertext_head_verified'
            write_private_json(journal, state)
        pin(drive, file_id, row['encrypted_revision'])
        row['recovery'] = verify_cipher_recovery(drive, file_id, row['encrypted_revision'], row, directory, key)
        row['phase'] = 'cloud_authenticated_recovery_passed'
        write_private_json(journal, state)
        row['plaintext_removed'] = purge_preserved_plaintext(drive, file_id, row)
        row['phase'] = 'original_plaintext_absent'
        write_private_json(journal, state)
    final = revisions(drive, file_id)
    allowed = {row['encrypted_revision'] for row in state['records'].values()}
    if {row['id'] for row in final} != allowed:
        raise DriveError('Unaccounted revision remains; keep sharing suspended')
    current = readback(drive, file_id)
    if current['headRevisionId'] not in allowed:
        raise DriveError('Final encrypted head is not verified')
    state.update(complete=True, completed_at=datetime.now(timezone.utc).isoformat(), final_revisions=final)
    write_private_json(journal, state)
    return state
