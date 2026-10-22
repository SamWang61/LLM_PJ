"""Plan or resume the full fixed-folder transfer while sharing remains suspended.

Requires an already complete private source manifest and complete legacy audit.
Does not restore ACLs. The operator must first recheck the fixed project's source
relationship and complete the separate, evidence-gated ACL restoration phase.
"""
import argparse
import json
from pathlib import Path
import threading

from drive_backup_acl import Drive, write_private_json
from drive_backup_auth import PRIVATE, SCOPE, session
from drive_backup_isolation import execution_lock
from drive_backup_payload import verify_source
from drive_backup_transfer import generated_ids
from drive_backup_sync import read_tree, validate_legacy_audit, build_plan, transfer


def private_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(PRIVATE.resolve()) or path == PRIVATE.resolve():
        raise ValueError('Full manifests and recovery state must remain in the private backup profile')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=private_path)
    parser.add_argument('--audit', required=True, type=private_path)
    parser.add_argument('--remediation-directory', required=True, type=private_path)
    parser.add_argument('--run-directory', required=True, type=private_path)
    parser.add_argument('--project-sources-reconfirmed', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.project_sources_reconfirmed:
        parser.error('First recheck the fixed project and its two original source objects')
    with execution_lock(PRIVATE):
        marker = json.loads((PRIVATE / 'active-isolation.json').read_text(encoding='utf8'))
        recovery = private_path(marker['run_directory'])
        if marker.get('sharing_restored'): raise ValueError('No suspended recovery state')
        original = json.loads((recovery / 'original-acl.json').read_text(encoding='utf8'))
        manifest = json.loads(args.manifest.read_text(encoding='utf8'))
        if (not manifest.get('complete') or manifest.get('source_errors')
                or Path(manifest['source_root']).resolve() != Path(r'C:\LLM\LLM_PJ').resolve()):
            raise ValueError('A complete manifest of the approved source is required')
        for row in manifest['files'].values(): private_path(row['payload_path'])
        verify_source(manifest['source_root'], manifest)
        base = session(); drive = Drive(base)
        snapshot = read_tree(drive, original)
        plan_path = args.run_directory / 'transfer-plan.json'
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding='utf8'))
            if plan['source_manifest'] != manifest:
                raise ValueError('Existing transfer plan belongs to a different source snapshot')
        else:
            audit = json.loads(args.audit.read_text(encoding='utf8'))
            validate_legacy_audit(snapshot, audit, args.remediation_directory)
            plan = build_plan(manifest, snapshot, lambda count: generated_ids(drive, count))
            args.run_directory.mkdir(parents=True, exist_ok=False)
            write_private_json(plan_path, plan)
        if not args.apply:
            print(json.dumps({'plan_ready': True, 'source_files': len(plan['files']),
                              'cloud_files_written': 0, 'sharing_restored': False}))
            return
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        credential_json = base.credentials.to_json(); local = threading.local()
        def factory():
            if not hasattr(local, 'drive'):
                local.drive = Drive(AuthorizedSession(Credentials.from_authorized_user_info(
                    json.loads(credential_json), scopes=[SCOPE])))
            return local.drive
        result = transfer(plan, factory, args.run_directory)
        print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'backup_completed': False, 'sharing_restored': False,
                          'error_type': type(error).__name__}))
        raise SystemExit(1) from None
