import copy
import pytest
import drive_backup_sync as sync
from drive_backup_acl import FOLDER,PROJECT,FOLDER_MIME,DriveError
from drive_backup_payload import prepare

def snapshot():
    return {'complete':True,'nodes':{
        FOLDER:{'id':FOLDER,'name':'LLM_PJ','mimeType':FOLDER_MIME},
        PROJECT:{'id':PROJECT,'name':'LLM_PJ','mimeType':'application/vnd.google-apps.project'},
        'old':{'id':'old','name':'existing.txt','parents':[FOLDER],'mimeType':'text/plain',
               'size':'3','md5Checksum':'keep','version':'1'},
        'extra':{'id':'extra','name':'extra.txt','parents':[FOLDER],'mimeType':'text/plain',
                 'size':'4','md5Checksum':'extra','version':'1'}},'additional_project_source_ids':[]}

def manifest(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'existing.txt').write_bytes(b'new')
    (root/'empty').mkdir()
    (root/'new.txt').write_bytes(b'new file')
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    return prepare(root,tmp_path/'private',key)

def make_plan(tmp_path):
    return sync.build_plan(manifest(tmp_path),snapshot(),lambda n:[f'new{i}' for i in range(n)])

def test_plan_preserves_existing_ids_and_extra_files_and_empty_directories(tmp_path):
    plan=make_plan(tmp_path)
    assert next(x for x in plan['files'] if x['path']=='existing.txt')['id']=='old'
    assert 'extra' in plan['original_ids'] and all(x['id']!='extra' for x in plan['files'])
    assert plan['folders'][0]['path']=='empty'

def test_incomplete_source_cannot_allocate_or_upload(tmp_path):
    data=manifest(tmp_path);data['complete']=False
    def never(n):raise AssertionError('Do not allocate IDs')
    with pytest.raises(ValueError,match='Incomplete'):sync.build_plan(data,snapshot(),never)

def test_duplicate_destination_names_and_file_directory_conflicts_fail(tmp_path):
    data=manifest(tmp_path);cloud=snapshot()
    cloud['nodes']['extra']['name']='EXISTING.txt'
    with pytest.raises(ValueError,match='Ambiguous'):sync.build_plan(data,cloud,lambda n:[])
    cloud=snapshot();cloud['nodes']['old']['mimeType']=FOLDER_MIME
    with pytest.raises(ValueError,match='conflict'):sync.build_plan(data,cloud,lambda n:[f'n{i}' for i in range(n)])

@pytest.mark.parametrize('failure',['none','checksum','extra_changed','missing','source_changed','folder_changed'])
def test_full_verification_requires_all_cloud_and_source_evidence(tmp_path,monkeypatch,failure):
    plan=make_plan(tmp_path);cloud=copy.deepcopy(plan['destination_before'])
    for row in plan['folders']:
        cloud['nodes'][row['id']]={'id':row['id'],'name':row['name'],'parents':[row['parent']],'mimeType':FOLDER_MIME}
    for row in plan['files']:
        expected=row['source']['payload']
        cloud['nodes'][row['id']]={'id':row['id'],'name':row['name'],'parents':[row['parent']],
            'mimeType':'text/plain','size':str(expected['size']),'md5Checksum':expected['md5'],
            'sha256Checksum':expected['sha256']}
    if failure=='checksum':cloud['nodes']['old']['sha256Checksum']='bad'
    if failure=='extra_changed':cloud['nodes']['extra']['version']='2'
    if failure=='missing':del cloud['nodes']['extra']
    if failure=='folder_changed':cloud['nodes'][plan['folders'][0]['id']]['name']='renamed'
    if failure=='source_changed':
        from pathlib import Path
        (Path(plan['source_manifest']['source_root'])/'existing.txt').write_bytes(b'changed')
    monkeypatch.setattr(sync,'read_tree',lambda *a:cloud)
    if failure=='none':
        receipt=sync.verify_complete(plan,None,tmp_path)
        assert receipt['cloud_consistent'] and not receipt['sharing_restored'] and not receipt['backup_completed']
    else:
        with pytest.raises((ValueError,DriveError)):sync.verify_complete(plan,None,tmp_path)
        assert not (tmp_path/'consistency-receipt.json').exists()


def test_legacy_audit_blocks_changed_files_and_unchecked_native_history(tmp_path):
    cloud=snapshot()
    for key in ('old','extra'):cloud['nodes'][key]['headRevisionId']='r_'+key
    audit={'complete':True,'native_sources':[], 'results':[
        {'file_id':key,'needs_encryption':False,'versions':[{'id':'r_'+key}]} for key in ('old','extra')]}
    assert sync.validate_legacy_audit(cloud,audit,tmp_path)
    cloud['nodes']['old']['headRevisionId']='changed'
    with pytest.raises(ValueError,match='changed'):sync.validate_legacy_audit(cloud,audit,tmp_path)
    cloud['nodes']['old']['headRevisionId']='r_old'
    cloud['additional_project_source_ids']=['doc']
    cloud['nodes']['doc']={'id':'doc','mimeType':'application/vnd.google-apps.document','version':'1'}
    with pytest.raises(ValueError,match='missing'):sync.validate_legacy_audit(cloud,audit,tmp_path)
    audit['native_sources']=[{'file_id':'doc','secret_detected':False,'version':'1',
                              'historical_native_revisions_checked':False}]
    with pytest.raises(ValueError,match='history'):sync.validate_legacy_audit(cloud,audit,tmp_path)
    audit['native_sources'][0]['historical_native_revisions_checked']=True
    assert sync.validate_legacy_audit(cloud,audit,tmp_path)


def test_folder_retry_uses_same_id_after_confirmed_absence(tmp_path,monkeypatch):
    plan=make_plan(tmp_path);cloud=copy.deepcopy(plan['destination_before']);requests=[]
    folder=plan['folders'][0]
    class API:
        def request(self,method,path,**kwargs):
            requests.append(kwargs['json']['id'])
            if len(requests)==1:raise DriveError('lost create response')
            row=kwargs['json'];cloud['nodes'][row['id']]=dict(row)
    def readback(api,key):
        if key not in cloud['nodes']:raise DriveError('Drive GET HTTP 404')
        return cloud['nodes'][key]
    def upload(api,path,key,metadata,expected,**kwargs):
        parent=next(r['parent'] for r in plan['files'] if r['id']==key)
        row={'id':key,'name':metadata['name'],'parents':[parent],'mimeType':'text/plain',
             'size':str(expected['size']),'md5Checksum':expected['md5'],'sha256Checksum':expected['sha256']}
        cloud['nodes'][key]=row;return row
    monkeypatch.setattr(sync,'read_tree',lambda *a:copy.deepcopy(cloud))
    monkeypatch.setattr(sync,'readback',readback)
    monkeypatch.setattr(sync,'upload',upload)
    monkeypatch.setattr(sync.time,'sleep',lambda _:None)
    receipt=sync.transfer(plan,API,tmp_path/'run',workers=1)
    assert requests==[folder['id'],folder['id']] and receipt['cloud_consistent']
    assert len(cloud['nodes'])==len(plan['original_ids'])+2
