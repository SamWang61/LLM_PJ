"""Reconcile a changed source after a fully verified suspended cloud transfer.

The previous plan's entire cloud output and destination extras must still match.
This does not waive source stability: the new complete manifest is checked before
and after transfer and again before restoration. Reuse encrypted payloads through
prepare(prior_manifest=...) to avoid uploading identical secrets every day.
"""
import argparse,json,threading
from drive_backup_acl import Drive,write_private_json
from drive_backup_auth import PRIVATE,SCOPE,session
from drive_backup_isolation import execution_lock
from drive_backup_run import private_path
from drive_backup_sync import read_tree,verify_cloud,build_plan,transfer
from drive_backup_payload import verify_source
from drive_backup_transfer import generated_ids

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previous-run',required=True,type=private_path)
    p.add_argument('--manifest',required=True,type=private_path)
    p.add_argument('--run-directory',required=True,type=private_path)
    a=p.parse_args()
    with execution_lock(PRIVATE):
        marker=json.loads((PRIVATE/'active-isolation.json').read_text(encoding='utf8'))
        if marker.get('sharing_restored'):raise ValueError('Reconciliation requires suspended sharing')
        previous=json.loads((a.previous_run/'transfer-plan.json').read_text(encoding='utf8'))
        manifest=json.loads(a.manifest.read_text(encoding='utf8'))
        if manifest['source_root']!=previous['source_manifest']['source_root']:raise ValueError('Source changed')
        for row in manifest['files'].values():private_path(row['payload_path'])
        verify_source(manifest['source_root'],manifest)
        base=session(); drive=Drive(base)
        current=read_tree(drive,previous['destination_before'])
        plan_path=a.run_directory/'transfer-plan.json'
        if plan_path.exists():
            plan=json.loads(plan_path.read_text(encoding='utf8'))
            if plan['source_manifest']!=manifest:raise ValueError('Resume requires the exact same manifest')
        else:
            verify_cloud(previous,current)
            a.run_directory.mkdir(exist_ok=False)
            write_private_json(a.run_directory/'previous-cloud-verified.json',current)
            plan=build_plan(manifest,current,lambda count:generated_ids(drive,count))
            write_private_json(plan_path,plan)
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        credential_json=base.credentials.to_json();local=threading.local()
        def factory():
            if not hasattr(local,'drive'):
                local.drive=Drive(AuthorizedSession(Credentials.from_authorized_user_info(json.loads(credential_json),scopes=[SCOPE])))
            return local.drive
        print(json.dumps(transfer(plan,factory,a.run_directory)))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'backup_completed':False,'sharing_restored':False,'error_type':type(error).__name__}))
        raise SystemExit(1) from None
