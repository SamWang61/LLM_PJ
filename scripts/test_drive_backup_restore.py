import copy
import json
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
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
        self.native_content=b'original native content'
        self.native_revisions=[{'id':'revision1','mimeType':'application/vnd.google-apps.document','modifiedTime':'2026-09-30T01:00:00Z'}]
        self.session=SimpleNamespace(get=lambda *a,**k:SimpleNamespace(status_code=200,content=self.native_content,close=lambda:None))
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
            self.nodes[key]['version']=str(int(self.nodes[key]['version'])+1)
            self.nodes[key]['modifiedTime']=f'2026-10-22T01:00:{len(self.posts):02d}Z'
            if self.lost:raise DriveError('response lost')
            return row
        assert method=='DELETE'
        self.deletes.append(path);pid=parts[3]
        self.nodes[key]['permissions']=[p for p in self.nodes[key]['permissions'] if p['id']!=pid]
        self.propagate(key,{'id':pid},True)
        self.nodes[key]['version']=str(int(self.nodes[key]['version'])+1)
        return {}
    def pages(self,path,key,**params):
        if path.endswith('/revisions'):
            yield from copy.deepcopy(self.native_revisions);return
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
    for row in isolated['nodes'].values():
        row['permissions']=[owner()];row['shared']=False
        row['version']='1';row['modifiedTime']='2026-10-22T00:00:00Z'
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


def setup_native(tmp_path):
    plan,original,nodes,recovery=setup(tmp_path)
    doc=node('native-doc','application/vnd.google-apps.document',permissions=[owner(),grant()])
    doc.update(version='1',modifiedTime='2026-10-22T00:00:00Z')
    original['additional_project_source_ids']=['native-doc'];original['nodes']['native-doc']=copy.deepcopy(doc)
    doc['permissions']=[owner()];doc['shared']=False;nodes['native-doc']=copy.deepcopy(doc)
    plan['destination_before']['additional_project_source_ids']=['native-doc']
    plan['destination_before']['nodes']['native-doc']=copy.deepcopy(doc)
    plan['original_ids'].append('native-doc')
    return plan,original,nodes,recovery


def test_direct_permission_mtime_changes_require_unchanged_native_content(tmp_path):
    plan,original,nodes,recovery=setup_native(tmp_path);api=FakeDrive(nodes)
    result=restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    assert result['complete'] and len(api.posts)==3
    assert api.nodes['native-doc']['modifiedTime']!=nodes['native-doc']['modifiedTime']
    before=json.loads((tmp_path/'native-content-before.json').read_text())
    after=json.loads((tmp_path/'native-content-after.json').read_text())
    assert before==after and set(before)=={'native-doc'}


@pytest.mark.parametrize('change',['text','revision'])
def test_native_content_or_format_revision_change_rolls_back_sharing(tmp_path,change):
    plan,original,nodes,recovery=setup_native(tmp_path);api=FakeDrive(nodes)
    request=api.request
    def corrupt(method,path,**kwargs):
        result=request(method,path,**kwargs)
        if method=='POST' and path.startswith('files/native-doc/'):
            if change=='text':api.native_content=b'changed document'
            else:api.native_revisions[0]['id']='new-format-revision'
        return result
    api.request=corrupt
    with pytest.raises(DriveError,match='content or revisions changed'):
        restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    state=json.loads((tmp_path/'acl-restore-journal.json').read_text())
    assert state['owner_only_verified'] and not state['complete']


def test_later_project_version_change_is_not_hidden_by_acl_mtime_exception(tmp_path,monkeypatch):
    plan,original,nodes,recovery=setup(tmp_path);api=FakeDrive(nodes)
    read_tree=restore.read_tree;calls=[]
    def changed(*args,**kwargs):
        snapshot=read_tree(*args,**kwargs);calls.append(True)
        if len(calls)==1:
            snapshot['nodes'][PROJECT]['version']=str(int(snapshot['nodes'][PROJECT]['version'])+1)
        return snapshot
    monkeypatch.setattr(restore,'read_tree',changed)
    with pytest.raises(DriveError,match='Native source changed'):
        restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    assert json.loads((tmp_path/'acl-restore-journal.json').read_text())['owner_only_verified']


@pytest.mark.parametrize('failure',['unsupported','empty_revisions','changed_during_export'])
def test_native_fingerprint_failure_blocks_before_any_share(tmp_path,failure):
    plan,original,nodes,recovery=setup_native(tmp_path);api=FakeDrive(nodes)
    if failure=='unsupported':
        for collection in (nodes,original['nodes'],plan['destination_before']['nodes'],api.nodes):
            collection['native-doc']['mimeType']='application/vnd.google-apps.spreadsheet'
    elif failure=='empty_revisions':api.native_revisions=[]
    else:
        export=api.session.get
        def changing(*args,**kwargs):
            api.nodes['native-doc']['version']='2';return export(*args,**kwargs)
        api.session.get=changing
    with pytest.raises(DriveError):restore.restore(plan,original,acl_plan(original),recovery,api,tmp_path)
    assert not api.posts


@pytest.mark.parametrize('stale_view', ['inline', 'complete'])
def test_disagreeing_acl_views_require_fresh_independent_agreement(tmp_path, stale_view):
    row = node('item', FOLDER_MIME, permissions=[owner(), grant()])
    row['shared'] = True
    api = FakeDrive({'item': row})
    explicit = api.permissions('item')
    indexed = api.row('item')
    expected = restore.normalized(explicit)
    if stale_view == 'inline':
        indexed['permissions'] = [owner()]; indexed['shared'] = False
    else:
        explicit = [owner()]
    restore.reconcile_acl_readback(indexed, explicit, expected, api, tmp_path)
    assert restore.normalized(indexed['permissions']) == expected
    proof = json.loads((tmp_path/'acl-reconciliation/item.json').read_text())
    assert proof['complete'] and len(proof['attempts']) == 1
    assert not api.posts and not api.deletes


@pytest.mark.parametrize('difference', ['role', 'discovery', 'inheritance', 'extra', 'missing_optional'])
def test_fresh_changed_rights_or_incomplete_semantics_are_never_waived(tmp_path, monkeypatch, difference):
    row = node('item', FOLDER_MIME, permissions=[owner(), grant()])
    row['shared'] = True
    expected = restore.normalized(row['permissions'])
    changed = copy.deepcopy(row)
    if difference == 'role': changed['permissions'][1]['role'] = 'writer'
    elif difference == 'discovery': changed['permissions'][1]['allowFileDiscovery'] = True
    elif difference == 'inheritance': changed['permissions'][1]['permissionDetails'] = [{'inherited':True}]
    elif difference == 'extra': changed['permissions'].append(grant(id='unexpected'))
    else: changed['permissions'][1].pop('allowFileDiscovery')
    api = FakeDrive({'item': changed})
    monkeypatch.setattr(restore.time, 'sleep', lambda _: None)
    with pytest.raises(DriveError, match='independent readback'):
        restore.reconcile_acl_readback(api.row('item'), api.permissions('item'), expected, api, tmp_path)
    proof = json.loads((tmp_path/'acl-reconciliation/item.json').read_text())
    assert not proof['complete'] and len(proof['attempts']) == 3


def test_stale_search_acl_does_not_discard_full_batch_or_fail_correct_restore(tmp_path):
    plan, original, nodes, recovery = setup(tmp_path)
    api = FakeDrive(nodes)
    pages = api.pages
    child = plan['files'][0]['id']
    def stale_once(*args, **kwargs):
        for row in pages(*args, **kwargs):
            if row['id'] == child and len(api.posts) == 2:
                row['permissions'] = [owner()]; row['shared'] = False
            yield row
    api.pages = stale_once
    result = restore.restore(plan, original, acl_plan(original), recovery, api, tmp_path)
    assert result['complete'] and not api.deletes
    full = json.loads((tmp_path/'full-acl-readback.json').read_text())
    assert set(full) == set(nodes)
    proof = json.loads((tmp_path/'acl-reconciliation'/f'{child}.json').read_text())
    assert proof['complete'] and len(proof['attempts']) == 1
