"""Authenticate all encrypted cloud payloads, then restore original ACLs.

Requires an existing full transfer plan, the immutable isolation recovery files,
and a current UI confirmation that the fixed project still has its two sources.
Every cloud/source gate is re-run before the first permission creation.
"""
import argparse
import json
from pathlib import Path
import threading
from drive_backup_acl import Drive, write_private_json
from drive_backup_auth import PRIVATE, SCOPE, session
from drive_backup_isolation import execution_lock
from drive_backup_run import private_path
from drive_backup_restore import recover_encrypted, restore
from drive_backup_sync import verify_complete


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory',required=True,type=private_path)
    parser.add_argument('--key',required=True,type=private_path)
    parser.add_argument('--project-sources-reconfirmed',action='store_true')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    if not args.project_sources_reconfirmed: parser.error('Reconfirm the fixed project source relationship first')
    with execution_lock(PRIVATE):
        marker_path=PRIVATE/'active-isolation.json'
        marker=json.loads(marker_path.read_text(encoding='utf8'))
        if marker.get('sharing_restored'): raise ValueError('Sharing has already been restored')
        isolation=private_path(marker['run_directory'])
        original=json.loads((isolation/'original-acl.json').read_text(encoding='utf8'))
        acl=json.loads((isolation/'restore-plan.json').read_text(encoding='utf8'))
        directory=args.run_directory
        plan=json.loads((directory/'transfer-plan.json').read_text(encoding='utf8'))
        if Path(plan['source_manifest']['source_root']).resolve()!=Path(r'C:\LLM\LLM_PJ').resolve():
            raise ValueError('Unapproved source')
        if not original['nodes'].keys() <= set(plan['original_ids']):
            raise ValueError('Transfer plan omitted an original object')
        base=session(); credential_json=base.credentials.to_json(); local=threading.local()
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        def factory():
            if not hasattr(local,'drive'):
                local.drive=Drive(AuthorizedSession(Credentials.from_authorized_user_info(json.loads(credential_json),scopes=[SCOPE])))
            return local.drive
        verify_complete(plan,factory(),directory)
        recovery=recover_encrypted(plan,factory,directory/'authenticated-recovery',args.key)
        if not args.restore:
            print(json.dumps({'cloud_recovery_complete':True,'encrypted_files':recovery['count'], 'sharing_restored':False})); return
        result=restore(plan,original,acl,recovery,factory(),directory)
        receipt=json.loads((directory/'consistency-receipt.json').read_text(encoding='utf8'))
        receipt.update(backup_completed=True,sharing_restored=True,encrypted_files_recovered=recovery['count'],
                       finished_at=result['finished_at'],acl_objects_verified=result['verified_objects'])
        write_private_json(directory/'completion-receipt.json',receipt)
        marker.update(phase='restored_and_verified',sharing_restored=True,completed_run_directory=str(directory),
                      completed_at=result['finished_at'])
        write_private_json(marker_path,marker)
        write_private_json(PRIVATE/'latest-complete-backup.json',{'run_directory':str(directory),**receipt})
        print(json.dumps(receipt))


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'backup_completed':False,'error_type':type(error).__name__,
            'inspect_private_journal':True}))
        raise SystemExit(1) from None
