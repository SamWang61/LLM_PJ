import hashlib
from pathlib import Path
import pytest
import drive_backup_remediate as remediation
from drive_backup_payload import hashes
from drive_backup_remediate import purge_preserved_plaintext

class NoRequests:
    def request(self,*a,**k):raise AssertionError('No API call permitted')

def test_pin_retries_only_after_readback_confirms_not_preserved(monkeypatch):
    events=[]
    class Drive:
        def request(self,method,*a,**k):
            events.append(method)
            return {'id':'revision','keepForever':events.count('PATCH')>=2}
    monkeypatch.setattr(remediation.time,'sleep',lambda _:None)
    assert remediation.pin(Drive(),'file','revision')['keepForever']
    assert events==['GET','PATCH','GET','GET','PATCH','GET']

@pytest.mark.parametrize('record', [{}, {'original_revision':'old','encrypted_revision':'new'},
    {'original_revision':'old','encrypted_revision':'new','recovery':{'authenticated':True}},
    {'original_revision':'old','encrypted_revision':'old','plaintext':{'sha256':'sha'},
     'recovery':{'authenticated':True,'cloud_revision':'old','plaintext_sha256':'sha'}}])
def test_plaintext_revision_cannot_be_purged_without_specific_cloud_recovery(record):
    with pytest.raises(ValueError):purge_preserved_plaintext(NoRequests(),'file',record)


@pytest.mark.parametrize('tamper',[False,True])
def test_full_remediation_preserves_id_and_never_purges_before_authenticated_cloud_copy(tmp_path,monkeypatch,tamper):
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    content={'old':b'secret test fixture'}
    head=['old'];events=[]
    def listing(drive,file_id):
        return [{'id':k,'size':str(len(v)),'md5Checksum':hashlib.md5(v).hexdigest()}
                for k,v in content.items()]
    def metadata(drive,file_id):
        return {'id':'file','name':'original.env','parents':['parent'],'headRevisionId':head[0]}
    def download(drive,file_id,target,expected,revision=None):
        data=content[revision]
        if tamper and revision=='cipher':data=data[:-1]+bytes([data[-1]^1])
        Path(target).write_bytes(data)
        events.append('download_'+revision)
        return hashes(Path(target))[0]
    def upload(drive,path,file_id,properties,expected):
        assert file_id=='file' and 'parents' not in properties
        content['cipher']=Path(path).read_bytes();head[0]='cipher';events.append('upload_cipher')
        return metadata(drive,file_id)
    class Drive:
        def request(self,method,path,**kwargs):
            if method=='DELETE':
                assert 'download_cipher' in events
                events.append('delete_old');del content['old'];return {}
            return {'id':'file','name':'original.env','parents':['parent'],
                    'mimeType':'text/plain','ownedByMe':True,'owners':[{'emailAddress':'cashsam@gmail.com'}],
                    'capabilities':{'canShare':True},'shared':False,
                    'permissions':[{'id':'owner','role':'owner','emailAddress':'cashsam@gmail.com'}]}
    monkeypatch.setattr(remediation,'revisions',listing)
    monkeypatch.setattr(remediation,'readback',metadata)
    monkeypatch.setattr(remediation,'download',download)
    monkeypatch.setattr(remediation,'upload',upload)
    monkeypatch.setattr(remediation,'pin',lambda *args:None)
    if tamper:
        with pytest.raises(Exception):remediation.remediate_file(Drive(),'file',tmp_path/'private',key)
        assert 'old' in content and 'delete_old' not in events
    else:
        result=remediation.remediate_file(Drive(),'file',tmp_path/'private',key)
        assert result['complete'] and set(content)=={'cipher'}
        assert events.index('download_cipher') < events.index('delete_old')
        assert result['records']['old']['recovery']['authenticated']
