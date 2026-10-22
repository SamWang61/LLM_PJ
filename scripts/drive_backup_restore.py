"""Evidence-gated restoration of the original fixed-project sharing.

Keep every input, journal and authenticated recovery download outside the source.
The caller holds backup-execution.lock throughout this phase. No keys or raw ACLs
are uploaded. Permission mutations are serial and ambiguous responses are read
back; a failed restoration revokes only the grants from this recovery plan.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from drive_backup_acl import (DriveError, FOLDER, PROJECT, PERMISSION_FIELDS, API,
    identifier, acl_semantics, plan as acl_plan, write_private_json, rate_limited, rate_backoff)
from drive_backup_isolation import check_owner, owner_only, permission_set, INLINE_FIELDS
from drive_backup_payload import verify_source, hashes
from drive_backup_sync import read_tree, verify_cloud, verify_complete
from drive_backup_transfer import download
from encrypted_backup import decrypt
from drive_backup_acl_batch import permissions_batch, permissions_many


def recover_encrypted(plan, drive_factory, directory, key, workers=8):
    """Download every encrypted outgoing payload and authenticate against source."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    def one(row):
        source = row['source']
        cipher = directory / (row['id'] + '.cipher')
        plain = directory / (row['id'] + '.restored')
        proof = directory / (row['id'] + '.json')
        # A resumed proof is accepted only with its independently downloaded bytes.
        download(drive_factory(), row['id'], cipher, source['payload'])
        if plain.exists():
            actual, _ = hashes(plain)
            if actual != source['plaintext']:
                raise DriveError('Existing private recovery differs; retain for inspection')
            plain.unlink()
        result = decrypt(cipher, plain, key)
        actual, _ = hashes(plain)
        if actual != source['plaintext']:
            raise DriveError('Remote authenticated recovery differs from source')
        plain.unlink()  # Only our authenticated, disposable private output.
        record = {'file_id': row['id'], 'authenticated': True,
                  'payload': source['payload'], 'plaintext': source['plaintext']}
        write_private_json(proof, record)
        return record
    rows = [r for r in plan['files'] if r['source']['encrypted']]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, rows))
    result = {'complete': True, 'count': len(results), 'results': results,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    write_private_json(directory / 'recovery-receipt.json', result)
    return result


def validate_recovery(plan, recovery):
    expected = {r['id']: r['source'] for r in plan['files'] if r['source']['encrypted']}
    rows = recovery.get('results', [])
    actual = {r['file_id']: r for r in rows}
    if (not recovery.get('complete') or len(rows) != len(actual)
            or actual.keys() != expected.keys()):
        raise ValueError('Complete independent encrypted recovery is required')
    for key, source in expected.items():
        row = actual[key]
        if (row.get('authenticated') is not True or row.get('payload') != source['payload']
                or row.get('plaintext') != source['plaintext']):
            raise ValueError('Recovery receipt belongs to another payload or source')


def normalized(rows):
    permission_set(rows)
    result = {}
    for row in rows:
        if row.get('deleted') or row.get('pendingOwner') or row.get('view'):
            raise DriveError('Unexpected permission state')
        inherited = None
        if row['role'] != 'owner':
            details = row.get('permissionDetails', [])
            values = {d.get('inherited') for d in details}
            if not details or len(values) != 1 or not values <= {True, False}:
                raise DriveError('Missing or mixed inheritance evidence')
            inherited = values.pop()
        result[row['id']] = (acl_semantics(row), inherited)
    return result


def expected_permissions(original, latest):
    """Original objects retain exact grants; new descendants inherit their parent."""
    expected = {key: normalized(row['permissions']) for key, row in original['nodes'].items()}
    pending = set(latest['nodes']) - set(expected)
    while pending:
        progressed = False
        for key in list(pending):
            row = latest['nodes'][key]
            parents = row.get('parents', [])
            if len(parents) != 1 or row.get('inheritedPermissionsDisabled'):
                raise DriveError('New object has unsupported inheritance')
            if parents[0] not in expected: continue
            expected[key] = {pid: (semantics, None if semantics['role']=='owner' else True)
                             for pid, (semantics, inherited) in expected[parents[0]].items()}
            pending.remove(key); progressed = True
        if not progressed: raise DriveError('Cannot resolve new object inheritance')
    return expected


def acl_views_match(row, permissions, expected):
    """Require exact identities and semantics; list metadata can omit inheritance."""
    inline = row.get('permissions', [])
    try:
        indexed = permission_set(inline)
        complete = permission_set(permissions)
        if (not indexed or indexed.keys() != complete.keys()
                or row.get('shared') is not any(p.get('role') != 'owner' for p in permissions)):
            return False
        for key, permission in indexed.items():
            if (any(permission.get(flag) for flag in ('deleted', 'pendingOwner', 'view'))
                    or acl_semantics(permission) != acl_semantics(complete[key])):
                return False
            if 'permissionDetails' in permission:
                if normalized([permission]) != normalized([complete[key]]):
                    return False
        return normalized(permissions) == expected
    except (DriveError, ValueError, KeyError, TypeError):
        return False


def reconcile_acl_readback(row, permissions, expected, drive, directory):
    """Resolve differing observations only with two fresh, agreeing endpoints.

    Never infer missing optional fields or waive a changed grant. Preserve every
    discrepancy before bounded read retries so a failed run remains diagnosable.
    """
    check_owner(row)
    if acl_views_match(row, permissions, expected):
        row['permissions'] = permissions
        return
    key = identifier(row['id'])
    proof = {'file_id': key, 'initial_metadata': dict(row),
             'initial_complete_permissions': permissions, 'attempts': [], 'complete': False}
    folder = Path(directory) / 'acl-reconciliation'
    folder.mkdir(exist_ok=True)
    path = folder / (key + '.json')
    write_private_json(path, proof)
    for attempt in range(3):
        if attempt:
            time.sleep(attempt)
        fresh_permissions = drive.permissions(key)
        fresh = drive.request('GET', f'files/{key}', params={
            'fields': INLINE_FIELDS + ',appProperties,headRevisionId',
            'includePermissionsForView': 'published'})
        proof['attempts'].append({'checked_at': datetime.now(timezone.utc).isoformat(),
            'metadata': fresh, 'complete_permissions': fresh_permissions})
        write_private_json(path, proof)
        check_owner(fresh)
        if any(fresh.get(k) != row.get(k) for k in ('id', 'name', 'mimeType', 'parents')):
            raise DriveError('Object identity changed during ACL reconciliation')
        if acl_views_match(fresh, fresh_permissions, expected):
            row.clear(); row.update(fresh); row['permissions'] = fresh_permissions
            proof['complete'] = True
            write_private_json(path, proof)
            return
    raise DriveError('Restored direct or inherited ACL differs after independent readback')


def native_document_fingerprint(drive, key):
    """Content/revision evidence is independent of ACL-updated modifiedTime."""
    key=identifier(key)
    fields={'fields':'id,mimeType,version'}
    before=drive.request('GET',f'files/{key}',params=fields)
    if before.get('mimeType')!='application/vnd.google-apps.document' or not before.get('version'):
        raise DriveError('Native document requires a supported content fingerprint')
    for attempt in range(8):
        response=drive.session.get(API+f'files/{key}/export',params={'mimeType':'text/plain'},
                                   timeout=60,allow_redirects=False)
        if rate_limited(response) and attempt<7:
            response.close();time.sleep(rate_backoff(attempt));continue
        try:
            if response.status_code!=200:raise DriveError('Native content export failed')
            digest=hashlib.sha256(response.content).hexdigest()
        finally:response.close()
        break
    revisions=list(drive.pages(f'files/{key}/revisions','revisions',pageSize=1000,
        fields='nextPageToken,revisions(id,mimeType,modifiedTime)'))
    if (not revisions or any(not r.get('id') or not r.get('modifiedTime') for r in revisions)
            or len({r['id'] for r in revisions})!=len(revisions)):
        raise DriveError('Native content revision evidence is incomplete')
    after=drive.request('GET',f'files/{key}',params=fields)
    if before!=after:raise DriveError('Native document changed during fingerprint')
    return {'text_sha256':digest,'revisions':sorted(revisions,key=lambda r:r['id'])}


def restore(plan, original, saved_acl_plan, recovery, drive, directory, drive_factory=None):
    """Restore original ACL only after fresh cloud, source and recovery gates.

    Does not update active-isolation.json; the CLI commits that marker only after
    this returns complete. On failure the immutable original restore plan remains.
    """
    directory = Path(directory)
    state_path = directory / 'acl-restore-journal.json'
    if state_path.exists():
        raise ValueError('Inspect existing restore journal before starting another attempt')
    calculated = acl_plan(original)
    if (not calculated['acl_plan_ready'] or calculated != saved_acl_plan):
        raise ValueError('Immutable original ACL and saved restore plan differ')
    validate_recovery(plan, recovery)
    if drive_factory:
        for rows in permissions_batch(drive,[FOLDER,PROJECT]).values():
            if len(rows)!=1 or rows[0]['role']!='owner':raise DriveError('Batch preflight is not owner-only')
    verify_complete(plan, drive, directory)
    latest = json.loads((directory/'verified-cloud.json').read_text(encoding='utf8'))
    expected = expected_permissions(original, latest)
    grants = sorted(saved_acl_plan['direct'], key=lambda r: (r['file_id']==FOLDER, r['file_id'],r['permission_id']))
    native_ids=[key for key,row in latest['nodes'].items()
                if row['mimeType'].startswith('application/vnd.google-apps.')
                and row['mimeType'] not in ('application/vnd.google-apps.folder','application/vnd.google-apps.project')]
    native_before={key:native_document_fingerprint(drive,key) for key in native_ids}
    write_private_json(directory/'native-content-before.json',native_before)
    state = {'complete':False, 'sharing_restored':False, 'phase':'gates_passed', 'operations':[],
             'started_at':datetime.now(timezone.utc).isoformat()}
    write_private_json(state_path, state)
    attempted = []
    try:
        for grant in grants:
            key = grant['file_id']
            before = permission_set(drive.permissions(key))
            if grant['permission_id'] in before:
                raise DriveError('Permission unexpectedly exists before restoration')
            operation = {**grant, 'phase':'requested'}
            state['operations'].append(operation); attempted.append(grant)
            write_private_json(state_path, state)
            try:
                drive.request('POST', f'files/{identifier(key)}/permissions',
                    params={'sendNotificationEmail':'false','fields':PERMISSION_FIELDS}, json=grant['restore'])
            except Exception as error:
                operation['response_error_type'] = type(error).__name__
            current = permission_set(drive.permissions(key))
            added = current.get(grant['permission_id'])
            if (current.keys() != before.keys() | {grant['permission_id']} or not added
                    or acl_semantics(added) != grant['restore']
                    or any(acl_semantics(current[pid]) != acl_semantics(row) for pid,row in before.items())):
                raise DriveError('Restored permission or existing ACL differs')
            operation['phase']='verified'; write_private_json(state_path,state)
        # Capture the metadata immediately after our verified permission calls.
        # Only their exact version increments may explain a native mtime change.
        changed_counts=Counter(r['file_id'] for r in grants)
        post_permission={}
        for key,count in changed_counts.items():
            row=drive.request('GET',f'files/{identifier(key)}',params={'fields':'id,mimeType,version,modifiedTime'})
            before=latest['nodes'][key]
            versions=[before.get('version'),row.get('version')]
            if (any(not isinstance(v,str) or not v.isascii() or not v.isdigit() for v in versions)
                    or int(versions[1])!=int(versions[0])+count or not row.get('modifiedTime')):
                raise DriveError('Unexpected metadata change during permission restoration')
            post_permission[key]=row
        write_private_json(directory/'post-permission-metadata.json',post_permission)
        full_acl = (permissions_many(latest['nodes'],drive_factory) if drive_factory
                    else {key:drive.permissions(key) for key in latest['nodes']})
        write_private_json(directory/'full-acl-readback.json', full_acl)
        def validator(row):
            reconcile_acl_readback(row, full_acl.get(row['id'], []),
                                   expected.get(row['id']), drive, directory)
        fresh = read_tree(drive, plan['destination_before'], acl_validator=validator)
        # ACL updates can increment version and modifiedTime on directly changed
        # objects. Blob hashes, native content/revisions, and exact post-operation
        # metadata distinguish these updates from content or concurrent changes.
        old = latest['nodes']
        if fresh['nodes'].keys() != old.keys(): raise DriveError('Cloud inventory changed during restoration')
        for key,row in fresh['nodes'].items():
            if any(row.get(k)!=old[key].get(k) for k in ('id','name','parents','mimeType','size','md5Checksum','sha256Checksum','headRevisionId')):
                raise DriveError('Cloud content changed during restoration')
            if row['mimeType'].startswith('application/vnd.google-apps.'):
                baseline=post_permission.get(key,old[key])
                fields=('version','modifiedTime') if key in post_permission else ('modifiedTime',)
                if any(row.get(k)!=baseline.get(k) for k in fields):
                    raise DriveError('Native source changed during restoration')
        native_after={key:native_document_fingerprint(drive,key) for key in native_ids}
        if native_after!=native_before:raise DriveError('Native document content or revisions changed')
        write_private_json(directory/'native-content-after.json',native_after)
        verify_source(plan['source_manifest']['source_root'], plan['source_manifest'])
        write_private_json(directory/'restored-cloud.json',fresh)
        state.update(complete=True, sharing_restored=True, phase='restored_and_verified',
                     verified_objects=len(fresh['nodes']), finished_at=datetime.now(timezone.utc).isoformat())
        write_private_json(state_path,state)
        return state
    except BaseException as error:
        state.update(phase='rolling_back', error_type=type(error).__name__, rollback=[])
        write_private_json(state_path,state)
        for grant in reversed(attempted):
            key=grant['file_id']; entry={'file_id':key,'permission_id':grant['permission_id']}
            try:
                current=permission_set(drive.permissions(key))
                found=current.get(grant['permission_id'])
                if found:
                    if acl_semantics(found)!=grant['restore']:
                        raise DriveError('Concurrent ACL change requires recovery review')
                    try: drive.request('DELETE',f"files/{identifier(key)}/permissions/{identifier(grant['permission_id'])}")
                    except Exception: pass
                if grant['permission_id'] in permission_set(drive.permissions(key)):
                    raise DriveError('Rollback deletion not verified')
                entry['removed']=True
            except Exception as rollback_error:
                entry['error_type']=type(rollback_error).__name__
            state['rollback'].append(entry); write_private_json(state_path,state)
        try:
            isolated=read_tree(drive, plan['destination_before'])
            write_private_json(directory/'failed-restore-isolated-cloud.json',isolated)
            state['owner_only_verified']=True
        except Exception:
            state['owner_only_verified']=False
        state['phase']='failed_closed' if state['owner_only_verified'] else 'manual_recovery_required'
        write_private_json(state_path,state)
        raise
