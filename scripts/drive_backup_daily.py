"""Run a new daily cycle after a verified completed fixed-folder backup.

The heartbeat must first recheck the fixed project's source list in Drive UI.
Remote content or ACL changes since the last completion fail at preflight and
require a new audit; they are never blindly overwritten. An interrupted active
isolation is resumed using its saved plans, not replaced by a new cycle.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,threading
from pathlib import Path
from drive_backup_auth import PRIVATE,SCOPE,session
from drive_backup_acl import Drive,DriveError,PROJECT,FOLDER,write_private_json,plan as acl_plan
from drive_backup_isolation import execution_lock,isolate,check_owner
from drive_backup_payload import prepare
from drive_backup_run import private_path
from drive_backup_sync import read_tree,build_plan,transfer
from drive_backup_restore import normalized,recover_encrypted,restore
from drive_backup_transfer import generated_ids


def unchanged_remote(previous,current):
    if not previous.get('complete') or not current.get('complete') or previous['nodes'].keys()!=current['nodes'].keys():
        raise DriveError('Remote inventory changed; confidential-content audit required')
    fields=('name','parents','mimeType','size','md5Checksum','sha256Checksum','headRevisionId','version','modifiedTime')
    for key,row in current['nodes'].items():
        if any(row.get(k)!=previous['nodes'][key].get(k) for k in fields):
            raise DriveError('Remote object changed; confidential-content audit required')
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-directory',required=True,type=private_path)
    p.add_argument('--key',required=True,type=private_path)
    p.add_argument('--project-sources-reconfirmed',action='store_true')
    args=p.parse_args()
    if not args.project_sources_reconfirmed:p.error('Reconfirm both fixed project sources in Drive UI first')
    with execution_lock(PRIVATE):
        marker_path=PRIVATE/'active-isolation.json'
        marker=json.loads(marker_path.read_text(encoding='utf8'))
        last=json.loads((PRIVATE/'latest-complete-backup.json').read_text(encoding='utf8'))
        if not marker.get('sharing_restored') or not last.get('backup_completed'):
            raise ValueError('Resume the existing isolation; do not replace recovery state')
        previous_dir=private_path(last['run_directory'])
        if marker.get('completed_run_directory')!=str(previous_dir):raise ValueError('Completion pointers disagree')
        previous=json.loads((previous_dir/'restored-cloud.json').read_text(encoding='utf8'))
        previous_plan=json.loads((previous_dir/'transfer-plan.json').read_text(encoding='utf8'))
        if hashlib.sha256(args.key.read_bytes()).hexdigest()[:16]!=previous_plan['source_manifest']['key_id']:
            raise ValueError('Use the saved recovery key; rotation needs a separate plan')
        policy=json.loads((Path(__file__).resolve().parents[1]/'config/drive-backup-policy.json').read_text(encoding='utf8'))
        if (policy['project_id']!=PROJECT or policy['folder_id']!=FOLDER
                or policy['source_root']!=r'C:\LLM\LLM_PJ'
                or policy['approved_exclusions']!=['MuscleCore分析資料/website/.pytest_cache']
                or set(policy['additional_project_source_ids'])!=set(previous['additional_project_source_ids'])):
            raise ValueError('Backup policy differs from the approved scope')
        base=session();credential_json=base.credentials.to_json();local=threading.local()
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        def factory():
            if not hasattr(local,'drive'):
                local.drive=Drive(AuthorizedSession(Credentials.from_authorized_user_info(json.loads(credential_json),scopes=[SCOPE])))
            return local.drive
        api=factory()
        def acl_validator(row):
            check_owner(row)
            permissions=row.get('permissions',[])
            if any(r['role']!='owner' and not r.get('permissionDetails') for r in permissions):
                permissions=api.permissions(row['id']);row['permissions']=permissions
            if (row['id'] not in previous['nodes']
                    or normalized(permissions)!=normalized(previous['nodes'][row['id']]['permissions'])):
                raise DriveError('Remote ACL changed; preserve and review before a new cycle')
        current=read_tree(api,previous,acl_validator=acl_validator)
        unchanged_remote(previous,current)
        directory=args.run_directory;directory.mkdir(exist_ok=False)
        write_private_json(directory/'previous-completion.json',last)
        manifest=prepare(policy['source_root'],directory/'source',args.key,
            excludes=policy['approved_exclusions'],prior_manifest=previous_plan['source_manifest'])
        # Recheck after local preparation; original ACL capture must be fresh.
        current=read_tree(api,previous,acl_validator=acl_validator)
        unchanged_remote(previous,current)
        isolation=directory/'isolation';isolation.mkdir()
        fresh_plan=acl_plan(current)
        if not fresh_plan['acl_plan_ready']:raise ValueError('Fresh ACL cannot be restored exactly')
        # Retain the previous pointer alongside all previous recovery data.
        write_private_json(directory/'previous-isolation-pointer.json',marker)
        marker={'run_directory':str(isolation),'phase':'starting_daily_isolation','sharing_restored':False,
            'restore_only_after_remediation_and_cloud_verification':True}
        # Save original recovery files before the active pointer or first mutation.
        write_private_json(isolation/'original-acl.json',current)
        write_private_json(isolation/'restore-plan.json',fresh_plan)
        write_private_json(marker_path,marker)
        isolate(api,current,isolation,current['additional_project_source_ids'])
        isolated=read_tree(api,current)
        transfer_plan=build_plan(manifest,isolated,lambda n:generated_ids(api,n))
        receipt=transfer(transfer_plan,factory,directory)
        recovery=recover_encrypted(transfer_plan,factory,directory/'authenticated-recovery',args.key)
        result=restore(transfer_plan,current,fresh_plan,recovery,api,directory)
        receipt.update(backup_completed=True,sharing_restored=True,encrypted_files_recovered=recovery['count'],
            finished_at=result['finished_at'],acl_objects_verified=result['verified_objects'])
        write_private_json(directory/'completion-receipt.json',receipt)
        marker.update(phase='restored_and_verified',sharing_restored=True,
            completed_run_directory=str(directory),completed_at=result['finished_at'])
        write_private_json(marker_path,marker)
        write_private_json(PRIVATE/'latest-complete-backup.json',{'run_directory':str(directory),**receipt})
        print(json.dumps(receipt))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'backup_completed':False,'error_type':type(error).__name__,'inspect_private_journal':True}))
        raise SystemExit(1) from None
