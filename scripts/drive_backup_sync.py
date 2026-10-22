"""Full relative-path planning, stable-ID transfer and cloud consistency gates.

This module never restores sharing. A successful receipt is required by the
separate owner-reviewed ACL recovery phase. Source exclusions must be approved.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import threading

from drive_backup_acl import (DriveError, FOLDER, PROJECT, FOLDER_MIME, identifier,
                              write_private_json)
from drive_backup_isolation import INLINE_FIELDS, owner_only
from drive_backup_payload import safe_relative, verify_source
from drive_backup_transfer import generated_ids, matches, upload, readback


def read_tree(drive, original, *, acl_validator=None):
    """Complete paginated owner-only readback, including every destination extra."""
    nodes = {}
    roots = {PROJECT, FOLDER, *original.get('additional_project_source_ids', [])}
    fields = INLINE_FIELDS + ',appProperties,headRevisionId'
    for key in roots:
        row = drive.request('GET', f'files/{identifier(key)}', params={
            'fields': fields, 'includePermissionsForView': 'published'})
        if any(row.get(k) != original['nodes'][key].get(k) for k in ('id', 'name', 'mimeType', 'parents')):
            raise DriveError('Fixed target identity changed')
        (acl_validator or owner_only)(row); nodes[key] = row
        permissions = drive.permissions(key)
        checked = dict(row, permissions=permissions)
        (acl_validator or owner_only)(checked)
    queue = [FOLDER]
    while queue:
        group, queue = queue[:20], queue[20:]
        query = '(' + ' or '.join(f"'{identifier(x)}' in parents" for x in group) + ') and trashed=false'
        for row in drive.pages('files', 'files', q=query, pageSize=1000,
                               fields=f'nextPageToken,incompleteSearch,files({fields})',
                               includePermissionsForView='published'):
            key = identifier(row.get('id'))
            if key in nodes or len(row.get('parents', [])) != 1 or row['parents'][0] not in group:
                raise DriveError('Duplicate or out-of-scope object')
            (acl_validator or owner_only)(row); nodes[key] = row
            if row['mimeType'] == FOLDER_MIME: queue.append(key)
    if not original['nodes'].keys() <= nodes.keys():
        raise DriveError('An original destination object is missing')
    return {'nodes': nodes, 'complete': True, 'project_id': PROJECT, 'folder_id': FOLDER,
            'additional_project_source_ids': list(roots - {PROJECT, FOLDER}),
            'captured_at': datetime.now(timezone.utc).isoformat()}


def relative_paths(snapshot):
    nodes, result = snapshot['nodes'], {FOLDER: ''}
    excluded = {PROJECT, *snapshot.get('additional_project_source_ids', [])}
    def resolve(key, seen):
        if key in result: return result[key]
        if key in seen or key in excluded or key not in nodes:
            raise ValueError('Cyclic, missing or external destination parent')
        row = nodes[key]; parents = row.get('parents', [])
        if len(parents) != 1: raise ValueError('Ambiguous destination parent')
        name = row.get('name', '')
        if not name or '/' in name or '\\' in name: raise ValueError('Unsafe destination name')
        prefix = resolve(parents[0], seen | {key})
        relative = prefix + '/' + name if prefix else name
        safe_relative(relative); result[key] = relative
        return relative
    for key in nodes:
        if key not in excluded: resolve(key, set())
    folded = [x.casefold() for x in result.values()]
    if len(set(folded)) != len(folded): raise ValueError('Ambiguous destination relative paths')
    return result


def build_plan(manifest, snapshot, id_factory):
    if not manifest.get('complete') or manifest.get('source_errors') or not snapshot.get('complete'):
        raise ValueError('Incomplete source or cloud inventory cannot start a full backup')
    paths = relative_paths(snapshot)
    existing = {value.casefold(): key for key, value in paths.items()}
    desired = sorted(manifest['directories'], key=lambda x: (x.count('/'), x)) + sorted(manifest['files'])
    if len({x.casefold() for x in desired}) != len(desired): raise ValueError('Source path collision')
    for value in desired: safe_relative(value)
    missing = [value for value in desired if value.casefold() not in existing]
    ids = id_factory(len(missing))
    if len(ids) != len(missing) or len(set(ids)) != len(ids) or set(ids) & set(snapshot['nodes']):
        raise ValueError('Generated destination IDs are not distinct')
    mapping = {value: existing[value.casefold()] for value in desired if value.casefold() in existing}
    mapping.update(zip(missing, ids)); mapping[''] = FOLDER
    folders, files = [], []
    for value in desired:
        key = mapping[value]; folder = value in manifest['directories']
        current = snapshot['nodes'].get(key)
        if current and (current['mimeType'] == FOLDER_MIME) != folder:
            raise ValueError('Source/destination file-directory conflict')
        parent = str(PurePosixPath(value).parent)
        parent = '' if parent == '.' else parent
        if parent not in mapping: raise ValueError('Source parent directory omitted')
        row = {'path': value, 'id': key, 'parent': mapping[parent],
               'name': PurePosixPath(value).name, 'create': current is None}
        if folder:
            folders.append(row)
        else:
            row['source'] = manifest['files'][value]; files.append(row)
    return {'schema': 1, 'folders': folders, 'files': files, 'original_ids': sorted(snapshot['nodes']),
            'destination_before': snapshot, 'source_manifest': manifest,
            'created_at': datetime.now(timezone.utc).isoformat(), 'sharing_restored': False}


def validate_legacy_audit(snapshot, audit, remediation_directory):
    """Require recorded checks for all existing blob versions, including extras."""
    if not audit.get('complete') or audit.get('errors') or any(x['secret_detected'] for x in audit['native_sources']):
        raise ValueError('Existing confidential-content audit is incomplete')
    if {r['file_id'] for r in audit['native_sources']} != set(snapshot.get('additional_project_source_ids', [])):
        raise ValueError('Additional project source audit is missing')
    for row in audit['native_sources']:
        if (not row.get('historical_native_revisions_checked')
                or row.get('version') != snapshot['nodes'][row['file_id']].get('version')):
            raise ValueError('Native source history is unverified or changed')
    rows = {row['file_id']: row for row in audit['results']}
    blobs = {key: row for key, row in snapshot['nodes'].items()
             if not row['mimeType'].startswith('application/vnd.google-apps.')}
    if rows.keys() != blobs.keys(): raise ValueError('Legacy audit does not cover the current blob set')
    for key, row in rows.items():
        if row.get('needs_encryption') or row.get('already_remediated'):
            state = json.loads((Path(remediation_directory) / key / 'journal.json').read_text(encoding='utf8'))
            if not state.get('complete') or state.get('file_id') != key:
                raise ValueError('Confidential content remediation is not complete')
            records = [r for r in state['records'].values()
                       if r.get('encrypted_revision') == blobs[key].get('headRevisionId')]
            if (len(records) != 1 or not records[0].get('plaintext_removed')
                    or not records[0].get('recovery', {}).get('authenticated')
                    or not matches(blobs[key], records[0]['ciphertext'])):
                raise ValueError('Remediated cloud head changed or lacks recovery proof')
        elif blobs[key].get('headRevisionId') not in {x['id'] for x in row['versions']}:
            raise ValueError('An audited ordinary file changed before backup')
    return True


def transfer(plan, drive_factory, directory, workers=12):
    """Caller holds the execution lock. Resume uses the same saved plan/IDs."""
    directory = Path(directory)
    if not plan['source_manifest'].get('complete') or plan['source_manifest'].get('source_errors'):
        raise ValueError('Incomplete source cannot be transferred as a full backup')
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / 'transfer-plan.json'
    if state_path.exists():
        if json.loads(state_path.read_text(encoding='utf8')) != plan:
            raise ValueError('Resume must use the exact saved transfer plan')
    else: write_private_json(state_path, plan)
    verify_source(plan['source_manifest']['source_root'], plan['source_manifest'])
    before = plan['destination_before']
    latest = read_tree(drive_factory(), before)
    allowed = set(plan['original_ids']) | {r['id'] for r in plan['folders'] + plan['files']}
    if not latest['nodes'].keys() <= allowed: raise ValueError('Unexpected concurrent cloud object')
    journal_lock = threading.Lock()
    def record(row):
        with journal_lock, (directory / 'transfer-events.jsonl').open('a', encoding='utf8') as stream:
            stream.write(json.dumps(row) + '\n'); stream.flush()
    def folder_one(row):
        drive = drive_factory()
        if row['id'] in latest['nodes']:
            current = latest['nodes'][row['id']]
        else:
            record({'id': row['id'], 'phase': 'folder_create_requested'})
            try:
                drive.request('POST', 'files', params={'fields': 'id'}, json={
                    'id': row['id'], 'name': row['name'], 'parents': [row['parent']], 'mimeType': FOLDER_MIME})
            except Exception: pass
            current = readback(drive, row['id'])
        if (current.get('name') != row['name'] or current.get('parents') != [row['parent']]
                or current.get('mimeType') != FOLDER_MIME): raise DriveError('Created folder identity mismatch')
        record({'id': row['id'], 'phase': 'folder_verified'})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for depth in sorted({r['path'].count('/') for r in plan['folders']}):
            list(pool.map(folder_one, [r for r in plan['folders'] if r['path'].count('/') == depth]))
    def file_one(row):
        drive = drive_factory(); source = row['source']; current = latest['nodes'].get(row['id'])
        if current and matches(current, source['payload']):
            record({'id': row['id'], 'phase': 'unchanged_hash_verified'}); return
        if current and current.get('version') != before['nodes'].get(row['id'], {}).get('version'):
            raise DriveError('Concurrent content change; do not overwrite')
        props = dict((current or {}).get('appProperties', {}))
        props.update(llmBackupEncrypted='v1' if source['encrypted'] else 'false',
                     llmBackupPlainSHA256=source['plaintext']['sha256'])
        metadata = {'name': row['name'], 'appProperties': props}
        if source['encrypted']: metadata['mimeType'] = 'application/octet-stream'
        if not current: metadata['parents'] = [row['parent']]
        record({'id': row['id'], 'phase': 'payload_upload_requested'})
        result = upload(drive, Path(source['payload_path']), row['id'], metadata, source['payload'],
                        create=current is None,
                        save_session=lambda url: write_private_json(directory / (row['id']+'.upload.json'), {'url': url}))
        if result.get('parents') != [row['parent']] or result.get('name') != row['name']:
            raise DriveError('Uploaded file identity mismatch')
        record({'id': row['id'], 'phase': 'cloud_payload_verified'})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(file_one, plan['files']))
    return verify_complete(plan, drive_factory(), directory)


def verify_complete(plan, drive, directory):
    fresh = read_tree(drive, plan['destination_before'])
    verify_cloud(plan, fresh)
    source = verify_source(plan['source_manifest']['source_root'], plan['source_manifest'])
    receipt = {'cloud_consistent': True, 'cloud_objects': len(fresh['nodes']), 'source': source,
               'source_files': len(plan['files']), 'sharing_restored': False, 'backup_completed': False,
               'checked_at': datetime.now(timezone.utc).isoformat()}
    write_private_json(Path(directory) / 'verified-cloud.json', fresh)
    write_private_json(Path(directory) / 'consistency-receipt.json', receipt)
    return receipt


def verify_cloud(plan, fresh):
    """Verify a saved snapshot independently of subsequent local changes.

    This permits a new full manifest to reconcile source changes after a transfer.
    It is NOT sufficient evidence for restoring sharing: verify_complete still
    requires the live source, and the restore gate checks it again.
    """
    if not fresh.get('complete'):
        raise DriveError('Cloud enumeration incomplete')
    expected = set(plan['original_ids']) | {r['id'] for r in plan['folders'] + plan['files']}
    if fresh['nodes'].keys() != expected: raise DriveError('Full cloud inventory differs')
    for row in plan['folders']:
        current = fresh['nodes'][row['id']]
        if (current.get('name') != row['name'] or current.get('parents') != [row['parent']]
                or current.get('mimeType') != FOLDER_MIME):
            raise DriveError('Cloud folder path mismatch')
    for row in plan['files']:
        current = fresh['nodes'][row['id']]
        if (current.get('name') != row['name'] or current.get('parents') != [row['parent']]
                or not matches(current, row['source']['payload'])):
            raise DriveError('Cloud file inventory/hash mismatch')
    written = {row['id'] for row in plan['files']}
    for key, old in plan['destination_before']['nodes'].items():
        if key not in written:
            fields = ('name','parents','mimeType') if old['mimeType'] == FOLDER_MIME else ('name','parents','mimeType','size','md5Checksum','sha256Checksum','version')
            if any(fresh['nodes'][key].get(k) != old.get(k) for k in fields):
                raise DriveError('Destination-only content changed')
    return True
