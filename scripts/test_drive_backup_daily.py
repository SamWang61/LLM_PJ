import copy
import json
import pytest
from drive_backup_acl import DriveError,PROJECT
from drive_backup_daily import unchanged_remote,verify_project_checkpoint,capture_project_checkpoint,review_revocation_transition


@pytest.mark.parametrize('change',['head','version','new','missing','incomplete'])
def test_changed_remote_state_requires_new_audit(change):
    before={'complete':True,'nodes':{'one':{'headRevisionId':'r1','version':'1','size':'10','md5Checksum':'a'}}}
    after=copy.deepcopy(before)
    assert unchanged_remote(before,after)
    if change=='head':after['nodes']['one']['headRevisionId']='r2'
    if change=='version':after['nodes']['one']['version']='2'
    if change=='new':after['nodes']['two']={}
    if change=='missing':after['nodes'].clear()
    if change=='incomplete':after['complete']=False
    with pytest.raises(DriveError,match='audit required'):unchanged_remote(before,after)


def project_snapshot():
    return {'complete':True,'nodes':{PROJECT:{'id':PROJECT,'name':'LLM_PJ',
        'mimeType':'application/vnd.google-apps.project','version':'35',
        'modifiedTime':'2026-10-22T04:13:15Z','parents':['parent'],
        'permissions':[{'id':'owner','role':'owner'}],
        'owners':[{'emailAddress':'owner@example.test'}],'ownedByMe':True,
        'trashed':False,'capabilities':{'canShare':True}}}}


def test_project_version_review_requires_reconfirmed_sources():
    before=project_snapshot();after=copy.deepcopy(before)
    after['nodes'][PROJECT]['version']='37'
    with pytest.raises(DriveError,match='audit required'):unchanged_remote(before,after)
    assert unchanged_remote(before,after,project_sources_reconfirmed=True)
    assert before['nodes'][PROJECT]['version']=='35'  # Previous proof stays immutable.


@pytest.mark.parametrize('change',['name','parents','modifiedTime','permissions',
    'owners','appProperties','mimeType','missing_version','rollback_version',
    'invalid_version','missing_permissions','additional_source'])
def test_project_review_never_waives_other_changes(change):
    before=project_snapshot();after=copy.deepcopy(before);row=after['nodes'][PROJECT]
    row['version']='37'
    if change=='name':row['name']='Other'
    elif change=='parents':row['parents']=['other']
    elif change=='modifiedTime':row['modifiedTime']='2026-10-22T05:13:15Z'
    elif change=='permissions':row['permissions'].append({'id':'reader','role':'reader'})
    elif change=='owners':row['owners']=[{'emailAddress':'other@example.test'}]
    elif change=='appProperties':row['appProperties']={'unexpected':'change'}
    elif change=='mimeType':row['mimeType']='application/vnd.google-apps.document'
    elif change=='missing_version':row.pop('version')
    elif change=='rollback_version':row['version']='34'
    elif change=='invalid_version':row['version']='unknown'
    elif change=='missing_permissions':row.pop('permissions')
    elif change=='additional_source':after['nodes']['new-source']={}
    with pytest.raises(DriveError,match='audit required'):
        unchanged_remote(before,after,project_sources_reconfirmed=True)


def test_reconfirmation_does_not_allow_other_native_document_version_change():
    before={'complete':True,'nodes':{'doc':{'id':'doc','mimeType':'application/vnd.google-apps.document','version':'1'}}}
    after=copy.deepcopy(before);after['nodes']['doc']['version']='2'
    with pytest.raises(DriveError,match='audit required'):
        unchanged_remote(before,after,project_sources_reconfirmed=True)


def test_reviewed_preflight_does_not_authorize_a_later_project_version():
    before=project_snapshot();accepted=copy.deepcopy(before)
    accepted['nodes'][PROJECT]['version']='37'
    assert unchanged_remote(before,accepted,project_sources_reconfirmed=True)
    assert unchanged_remote(accepted,copy.deepcopy(accepted))
    later=copy.deepcopy(accepted);later['nodes'][PROJECT]['version']='38'
    with pytest.raises(DriveError,match='audit required'):unchanged_remote(accepted,later)


def test_source_confirmation_checkpoint_accepts_only_unchanged_project():
    before=project_snapshot()['nodes'][PROJECT]
    checkpoint={k:before[k] for k in ('id','mimeType','version','modifiedTime')}
    verify_project_checkpoint(checkpoint,copy.deepcopy(before))


@pytest.mark.parametrize('change',['id','mimeType','version','modifiedTime','missing_version'])
def test_long_acl_scan_cannot_reuse_confirmation_for_changed_project(change):
    before=project_snapshot()['nodes'][PROJECT]
    after=copy.deepcopy(before)
    if change=='missing_version':after.pop('version')
    else:after[change]='changed'
    with pytest.raises(DriveError,match='reconfirm sources'):
        verify_project_checkpoint(before,after)


def test_source_checkpoint_is_durable_before_later_acl_failure(tmp_path):
    row=project_snapshot()['nodes'][PROJECT]
    expected={k:row[k] for k in ('id','mimeType','version','modifiedTime')}
    class API:
        def request(self, method, path, **kwargs):
            assert method=='GET' and path==f'files/{PROJECT}'
            return copy.deepcopy(expected)
    with pytest.raises(DriveError,match='long scan failed'):
        captured=capture_project_checkpoint(API(),tmp_path)
        assert captured==expected
        assert json.loads((tmp_path/'source-confirmation-project-checkpoint.json').read_text())==expected
        raise DriveError('long scan failed')
    assert json.loads((tmp_path/'source-confirmation-project-checkpoint.json').read_text())==expected


def test_existing_checkpoint_is_not_replaced_or_refetched(tmp_path):
    path=tmp_path/'source-confirmation-project-checkpoint.json';path.write_text('original')
    class API:
        def request(self,*args,**kwargs):raise AssertionError('must not refetch')
    with pytest.raises(ValueError,match='Never replace'):
        capture_project_checkpoint(API(),tmp_path)
    assert path.read_text()=='original'


def test_incomplete_project_checkpoint_is_not_persisted(tmp_path):
    class API:
        def request(self,*args,**kwargs):return {'id':PROJECT}
    with pytest.raises(DriveError,match='reconfirm sources'):
        capture_project_checkpoint(API(),tmp_path)
    assert not (tmp_path/'source-confirmation-project-checkpoint.json').exists()


def revocation_case():
    from drive_backup_acl import FOLDER,plan
    from test_drive_backup_acl import node,owner,grant
    before={'complete':True,'captured_at':'2026-10-23T16:00:00+00:00',
        'project_id':PROJECT,'folder_id':FOLDER,'additional_project_source_ids':['doc'],
        'nodes':{
            PROJECT:node(PROJECT,'application/vnd.google-apps.project',permissions=[owner(),grant()]),
            FOLDER:node(FOLDER,'application/vnd.google-apps.folder',permissions=[owner(),grant()]),
            'doc':node('doc','application/vnd.google-apps.document',permissions=[owner(),grant()]),
            'child':node('child','text/plain',[FOLDER],[owner(),grant(permissionDetails=[{'inherited':True}])])}}
    for row in before['nodes'].values():
        row.update(version='10',modifiedTime='2026-10-23T15:00:00Z',shared=True)
    before['nodes']['child'].update(size='8',md5Checksum='old-md5',sha256Checksum='old-sha',headRevisionId='r1')
    after=copy.deepcopy(before)
    for key,row in after['nodes'].items():
        row.update(version='11',permissions=[owner()],shared=False)
        if key!='child':row['modifiedTime']='2026-10-23T16:10:01Z'
    state={'phase':'isolation_verified','complete':True,'started_at':'2026-10-23T16:10:00+00:00',
        'permissions_removed_at':'2026-10-23T16:10:02+00:00',
        'operations':[{**r,'status':'verified_absent'} for r in plan(before)['direct']]}
    native={'doc':{'text_sha256':'unchanged-text','revisions':[{'id':'content-r1','modifiedTime':'2026-10-23T15:00:00Z'}]}}
    return before,after,state,native


def test_exact_inherited_version_increment_requires_unchanged_blob_content():
    before,after,state,native=revocation_case()
    proof=review_revocation_transition(before,after,state,native,copy.deepcopy(native))
    assert proof['complete'] and proof['objects']==4 and proof['direct_objects']==3
    child=next(r for r in proof['records'] if r['id']=='child')
    assert child['removed_grants']==1 and not child['directly_changed']
    assert before['nodes']['child']['version']=='10'


def test_unchanged_direct_modified_time_needs_no_time_exception():
    before,after,state,native=revocation_case()
    for key,row in after['nodes'].items():
        row['modifiedTime']=before['nodes'][key]['modifiedTime']
    assert review_revocation_transition(before,after,state,native,copy.deepcopy(native))['complete']


@pytest.mark.parametrize('change',['hash','revision','mtime','extra_version','missing_version','missing_mtime',
                                  'parent','app_properties','new_object','owner','grant','direct_mtime'])
def test_permission_version_accounting_never_waives_other_differences(change):
    before,after,state,native=revocation_case();row=after['nodes']['child']
    if change=='hash':row['sha256Checksum']='changed'
    elif change=='revision':row['headRevisionId']='r2'
    elif change=='mtime':row['modifiedTime']='2026-10-23T16:10:01Z'
    elif change=='extra_version':row['version']='12'
    elif change=='missing_version':row.pop('version')
    elif change=='missing_mtime':row.pop('modifiedTime')
    elif change=='parent':row['parents']=['elsewhere']
    elif change=='app_properties':row['appProperties']={'unreviewed':'change'}
    elif change=='new_object':after['nodes']['new']=copy.deepcopy(row)
    elif change=='owner':row['permissions'][0]['id']='unexpected-owner'
    elif change=='grant':
        from test_drive_backup_acl import grant
        row['permissions'].append(grant());row['shared']=True
    elif change=='direct_mtime':after['nodes'][PROJECT]['modifiedTime']='2026-10-23T16:10:03Z'
    with pytest.raises(DriveError):
        review_revocation_transition(before,after,state,native,copy.deepcopy(native))


@pytest.mark.parametrize('change',['text','revisions','missing_native','missing_operation','unverified_operation','duplicate_operation'])
def test_native_content_and_each_original_revocation_need_independent_evidence(change):
    before,after,state,native=revocation_case();fresh=copy.deepcopy(native)
    if change=='text':fresh['doc']['text_sha256']='changed'
    elif change=='revisions':fresh['doc']['revisions'].append({'id':'format-r2'})
    elif change=='missing_native':fresh={}
    elif change=='missing_operation':state['operations'].pop()
    elif change=='unverified_operation':state['operations'][0]['status']='requested'
    elif change=='duplicate_operation':state['operations'].append(copy.deepcopy(state['operations'][0]))
    with pytest.raises(DriveError):
        review_revocation_transition(before,after,state,native,fresh)
