import hashlib
import json
import struct

from bson import BSON
import pytest

from atlas_snapshot_backup import bson_documents, logical_metadata, require_local_target, validate_backup


def fixture_backup(tmp_path):
    data=BSON.encode({'_id':1,'value':'kept'})
    schema=BSON.encode({'name':'items','type':'collection','options':{},'indexes':[], 'search_indexes':[]})
    (tmp_path/'0000.bson').write_bytes(data)
    (tmp_path/'0000.metadata.bson').write_bytes(schema)
    row={'collection':'items','data':'0000.bson','metadata':'0000.metadata.bson',
         'documents':1,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
         'metadata_sha256':hashlib.sha256(schema).hexdigest()}
    manifest={'version':1,'complete':True,'search_indexes':0,'collections':[row]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    return manifest


def save(tmp_path, manifest):
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))


def test_private_backup_integrity_and_raw_bson(tmp_path):
    fixture_backup(tmp_path)
    report, schemas=validate_backup(tmp_path)
    assert report['collections'][0]['documents']==1
    assert next(bson_documents(tmp_path/'0000.bson'))['_id']==1
    assert schemas[0]['name']=='items'


@pytest.mark.parametrize('path',['../escape.bson','/absolute.bson','0000.bson/../other','..\\escape.bson'])
def test_reject_paths_before_target_write(tmp_path,path):
    manifest=fixture_backup(tmp_path);manifest['collections'][0]['data']=path;save(tmp_path,manifest)
    with pytest.raises(ValueError,match='path'):validate_backup(tmp_path)


def test_reject_corrupt_bytes(tmp_path):
    fixture_backup(tmp_path);(tmp_path/'0000.bson').write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash'):validate_backup(tmp_path)


def test_reject_count_mismatch(tmp_path):
    manifest=fixture_backup(tmp_path);manifest['collections'][0]['documents']=2;save(tmp_path,manifest)
    with pytest.raises(ValueError,match='count'):validate_backup(tmp_path)


def test_reject_duplicate_collection(tmp_path):
    manifest=fixture_backup(tmp_path);manifest['collections'].append(manifest['collections'][0]);save(tmp_path,manifest)
    with pytest.raises(ValueError,match='Duplicate'):validate_backup(tmp_path)


def test_search_index_requires_atlas_restore(tmp_path):
    manifest=fixture_backup(tmp_path);manifest['search_indexes']=1;save(tmp_path,manifest)
    with pytest.raises(ValueError,match='Atlas Search'):validate_backup(tmp_path)


@pytest.mark.parametrize('raw',[b'\x01',struct.pack('<i',4),struct.pack('<i',100)+b'\0'])
def test_truncated_bson_rejected(tmp_path,raw):
    p=tmp_path/'bad.bson';p.write_bytes(raw)
    with pytest.raises(ValueError):list(bson_documents(p))


def test_compound_index_order_is_significant():
    first={'name':'items','type':'collection','options':{},'indexes':[{'name':'compound','key':{'a':1,'b':-1}}]}
    second={**first,'indexes':[{'name':'compound','key':{'b':-1,'a':1}}]}
    assert logical_metadata(first)!=logical_metadata(second)


class LocalClient:
    address=('127.0.0.1',27017)
    admin=None
    def __init__(self,ttl=False,bind='127.0.0.1',existing=False):
        self.admin=self;self.ttl=ttl;self.bind=bind;self.existing=existing
    def command(self,command):
        return {'parsed':{'net':{'bindIp':self.bind}}} if command=='getCmdLineOpts' else {'ttlMonitorEnabled':self.ttl}
    def list_database_names(self):return ['sam_n14_restore_'+'a'*32] if self.existing else []


def test_reject_production_namespace():
    with pytest.raises(ValueError,match='generated'):require_local_target(LocalClient(),'vibecart_ai')


def test_reject_remote_restore_target():
    client=LocalClient();client.address=('atlas.example',27017)
    with pytest.raises(ValueError,match='localhost'):require_local_target(client,'sam_n14_restore_'+'a'*32)


@pytest.mark.parametrize('client',[LocalClient(ttl=True),LocalClient(bind='0.0.0.0'),LocalClient(existing=True)])
def test_reject_ttl_public_binding_and_existing_db(client):
    with pytest.raises(ValueError):require_local_target(client,'sam_n14_restore_'+'a'*32)
