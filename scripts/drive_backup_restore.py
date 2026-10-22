"""Evidence-gated restoration of the original fixed-project sharing.

Keep every input, journal and authenticated recovery download outside the source.
The caller holds backup-execution.lock throughout this phase. No keys or raw ACLs
are uploaded. Permission mutations are serial and ambiguous responses are read
back; a failed restoration revokes only the grants from this recovery plan.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from drive_backup_acl import (DriveError, FOLDER, PROJECT, PERMISSION_FIELDS,
    identifier, acl_semantics, plan as acl_plan, write_private_json)
from drive_backup_isolation import check_owner, owner_only, permission_set
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
        full_acl = (permissions_many(latest['nodes'],drive_factory) if drive_factory
                    else {key:drive.permissions(key) for key in latest['nodes']})
        def validator(row):
            check_owner(row)
            inline = row.get('permissions', [])
            permission_set(inline)
            permissions = full_acl.get(row['id'], [])
            if {p['id']:acl_semantics(p) for p in inline}!={p['id']:acl_semantics(p) for p in permissions}:
                raise DriveError('ACL changed between full and inline readback')
            row['permissions'] = permissions
            if normalized(permissions) != expected.get(row['id']):
                raise DriveError('Restored direct or inherited ACL differs')
        fresh = read_tree(drive, plan['destination_before'], acl_validator=validator)
        # ACL updates increment version. Content is checked by size/hash for all
        # blobs; native sources have no content mutation in this operation.
        old = latest['nodes']
        if fresh['nodes'].keys() != old.keys(): raise DriveError('Cloud inventory changed during restoration')
        for key,row in fresh['nodes'].items():
            if any(row.get(k)!=old[key].get(k) for k in ('id','name','parents','mimeType','size','md5Checksum','sha256Checksum','headRevisionId')):
                raise DriveError('Cloud content changed during restoration')
            if row['mimeType'].startswith('application/vnd.google-apps.') and row.get('modifiedTime') != old[key].get('modifiedTime'):
                raise DriveError('Native source changed during restoration')
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
