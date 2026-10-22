import copy
import pytest
from drive_backup_acl import DriveError,PROJECT
from drive_backup_daily import unchanged_remote


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
