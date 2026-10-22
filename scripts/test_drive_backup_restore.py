import copy
import json
from pathlib import Path
import re
import shutil
import pytest

import drive_backup_restore as restore
from drive_backup_acl import FOLDER, PROJECT, FOLDER_MIME, DriveError, plan as acl_plan
from drive_backup_payload import prepare
from drive_backup_sync import build_plan
from test_drive_backup_acl import owner, grant, node


class FakeDrive:
    def __init__(self,nodes,fail_at=0,lost=False,inline_details=True):
        self.nodes=copy.deepcopy(nodes); self.posts=[]; self.deletes=[]
        self.fail_at=fail_at;self.lost=lost;self.inline_details=inline_details
    def permissions(self,key): return copy.deepcopy(self.nodes[key]['permissions'])
    def row(self,key):
        row=copy.deepcopy(self.nodes[key])
        row['shared']=len(row['permissions'])>1
        if not self.inline_details:
            for p in row['permissions']:p.pop('permissionDetails',None)
        return row
    def children(self,key):
        return [r['id'] for r in self.nodes.values() if r.get('parents')==[key]]
    def propagate(self,key,p,delete=False):
        for child in self.children(key):
            rows=self.nodes[child]['permissions']
            rows[:]=[x for x in rows if x['id']!=p['id']]
            if not delete:rows.append(dict(p,permissionDetails=[{'inherited':True}]))
            self.propagate(child,p,delete)
    def request(self,method,path,**kwargs):
        parts=path.split('/');key=parts[1]
        if method=='GET':return self.row(key)
        if method=='POST':
            self.posts.append(path)
            if len(self.posts)==self.fail_at:raise DriveError('rejected')
            body=kwargs['json'];pid='reader-id' if body['type']=='anyone' else 'writer-id'
            row=dict(body,id=pid,permissionDetails=[{'inherited':False}])
            self.nodes[key]['permissions'].append(row);self.propagate(key,row)
            if self.lost:raise DriveError('response lost')
            return row
        assert method=='DELETE'
        self.deletes.append(path);pid=parts[3]
        self.nodes[key]['permissions']=[p for p in self.nodes[key]['permissions'] if p['id']!=pid]
        self.propagate(key,{'id':pid},True)
        return {}
    def pages(self,path,key,**params):
        parents=set(re.findall(r"'([^']+)' in parents",params['q']))
        for key,row in self.nodes.items():
            if row.get('parents') and row['parents'][0] in parents:yield self.row(key)


def setup(tmp_path):
    root=tmp_path/'source';root.mkdir();(root/'readme').write_bytes(b'hello')
    (root/'empty').mkdir();key=tmp_path/'key';key.write_bytes(b'k'*32)
    manifest=prepare(root,tmp_path/'private',key)
    writer=grant(id='writer-id',type='user',role='writer',emailAddress='team@example.invalid')
    writer.pop('allowFileDiscovery')
    original={'complete':True,'project_id':PROJECT,'folder_id':FOLDER,'additional_project_source_ids':[],
        'nodes':{PROJECT:node(PROJECT,'application/vnd.google-apps.project',permissions=[owner(),writer]),
                 FOLDER:node(FOLDER,FOLDER_MIME,permissions=[owner(),grant()])}}
    isolated=copy.deepcopy(original)
    for row in isolated['nodes'].values():row['permissions']=[owner()];row['shared']=False
    plan=build_plan(manifest,isolated,lambda n:[f'new{i}' for i in range(n)])
    nodes=copy.deepcopy(isolated['nodes'])
    for row in plan['folders']:
        nodes[row['id']]=node(row['id'],FOLDER_MIME,[row['parent']],[owner()])
        nodes[row['id']]['name']=row['name']
    for row in plan['files']:
        expected=row['source']['payload']
        nodes[row['id']]=node(row['id'],'text/plain',[row['parent']],[owner()])
        nodes[row['id']].update(name=row['name'],size=str(expected['size']),md5Checksum=expected['md5'],sha256Checksum=expected['sha256'])
    return plan,original,nodes,{'complete':True,'results':[]}


@pytest.mark.parametrize('lost,inline',[(False,True),(True,True),(False,False)])
def test_restore_exact_grants_and_new_descendant_inheritance(tmp_path,lost,inline):
    plan,original,nodes,recovery=setup(tmp_path)
    api=FakeDrive(nodes,lost=lost,inline_details=inline)
    result=restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    assert result['complete'] and result['sharing_restored'] and result['verified_objects']==4
    assert len(api.posts)==2 and not api.deletes


@pytest.mark.parametrize('failure',['cloud','source','recovery','original_acl'])
def test_gate_failure_never_restores_any_permission(tmp_path,failure):
    plan,original,nodes,recovery=setup(tmp_path);saved=acl_plan(original)
    if failure=='cloud':nodes[plan['files'][0]['id']]['size']='999'
    if failure=='source':(Path(plan['source_manifest']['source_root'])/'readme').write_bytes(b'changed')
    if failure=='recovery':recovery['complete']=False
    if failure=='original_acl':saved['direct']=[]
    api=FakeDrive(nodes)
    with pytest.raises((DriveError,ValueError)):restore.restore(plan,original,saved,recovery,api,tmp_path)
    assert not api.posts and not api.deletes


def test_partial_restore_failure_revokes_attempted_grants_and_verifies_owner_only(tmp_path):
    plan,original,nodes,recovery=setup(tmp_path);api=FakeDrive(nodes,fail_at=2)
    with pytest.raises(DriveError):restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    state=json.loads((tmp_path/'acl-restore-journal.json').read_text())
    assert state['phase']=='failed_closed' and state['owner_only_verified'] and not state['complete']
    assert all(len(x['permissions'])==1 for x in api.nodes.values())


def test_unexpected_direct_grant_on_new_child_is_not_accepted(tmp_path):
    plan,original,nodes,recovery=setup(tmp_path);api=FakeDrive(nodes)
    original_propagate=api.propagate
    def corrupt(key,p,delete=False):
        original_propagate(key,p,delete)
        if not delete and key==FOLDER:
            api.nodes[plan['files'][0]['id']]['permissions'][-1]['permissionDetails']=[{'inherited':False}]
    api.propagate=corrupt
    with pytest.raises(DriveError,match='inherited ACL'):restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    assert json.loads((tmp_path/'acl-restore-journal.json').read_text())['owner_only_verified']


def test_every_encrypted_payload_requires_cloud_download_and_authentication(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir();(root/'.env').write_bytes(b'private-fixture')
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    manifest=prepare(root,tmp_path/'private',key)
    row={'id':'cipher','source':manifest['files']['.env']};plan={'files':[row]}
    downloads=[]
    def download(api,ident,dest,expected):
        downloads.append(ident);shutil.copyfile(row['source']['payload_path'],dest)
    monkeypatch.setattr(restore,'download',download)
    proof=restore.recover_encrypted(plan,lambda:None,tmp_path/'recovery',key)
    restore.validate_recovery(plan,proof)
    assert downloads==['cipher'] and proof['count']==1 and not list((tmp_path/'recovery').glob('*.restored'))
    proof['results'][0]['payload']['sha256']='wrong'
    # Detached copy avoids aliasing the expected source in this test.
    copied=copy.deepcopy(plan);copied['files'][0]['source']['payload']['sha256']='original'
    with pytest.raises(ValueError):restore.validate_recovery(copied,proof)
