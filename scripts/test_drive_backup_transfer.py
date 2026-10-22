from pathlib import Path
from types import SimpleNamespace
import pytest
from drive_backup_acl import DriveError
from drive_backup_payload import hashes
from drive_backup_transfer import acknowledged, matches, upload, validate_upload_url

def test_partial_or_conflicting_hashes_do_not_pass():
    expected={'size':3,'sha256':'abc','md5':'def'}
    assert matches({'size':'3','sha256Checksum':'abc'},expected)
    assert not matches({'size':'3'},expected)
    assert not matches({'size':'3','sha256Checksum':'abc','md5Checksum':'wrong'},expected)
    assert not matches({'size':'3','sha256Checksum':'abc','trashed':True},expected)

@pytest.mark.parametrize('url',['http://www.googleapis.com/upload/drive/v3/files',
    'https://www.googleapis.com.evil.test/upload/drive/v3/files',
    'https://evil.test/upload/drive/v3/files','https://www.googleapis.com/other'])
def test_upload_tokens_cannot_be_forwarded_to_another_host(url):
    with pytest.raises(DriveError):validate_upload_url(url)

def test_partial_acknowledgements_and_finished_response():
    assert acknowledged(SimpleNamespace(status_code=308,headers={'Range':'bytes=0-511'}),1024)==512
    assert acknowledged(SimpleNamespace(status_code=308,headers={}),1024)==0
    assert acknowledged(SimpleNamespace(status_code=200),1024)==1024
    with pytest.raises(DriveError): acknowledged(SimpleNamespace(status_code=308,headers={'Range':'bytes=3-511'}),1024)

def test_lost_upload_response_requires_matching_independent_readback(tmp_path):
    path=tmp_path/'payload';path.write_bytes(b'fixture')
    expected,_=hashes(path)
    class Session:
        def request(self,*args,**kwargs):raise TimeoutError()
    class Drive:
        session=Session()
        def request(self,*args,**kwargs):
            return {'id':'fixed','size':str(expected['size']),'sha256Checksum':expected['sha256']}
    assert upload(Drive(),path,'fixed',{},expected)['id']=='fixed'
    wrong=dict(expected,sha256='wrong')
    with pytest.raises(ValueError,match='changed'): upload(Drive(),path,'fixed',{},wrong)

def test_uncertain_create_uses_preassigned_id_and_fails_closed(tmp_path):
    path=tmp_path/'payload';path.write_bytes(b'fixture');expected,_=hashes(path)
    calls=[]
    class Session:
        def request(self,*args,**kwargs):calls.append(kwargs['data']);raise TimeoutError()
    class Drive:
        session=Session()
        def request(self,*args,**kwargs):raise DriveError('missing')
    with pytest.raises(DriveError,match='not verified'):upload(Drive(),path,'stableid',{},expected,create=True)
    assert len(calls)==1 and b'"id": "stableid"' in calls[0]


def test_resumable_upload_queries_received_range_after_lost_response(tmp_path):
    path=tmp_path/'large';path.write_bytes(b'x'*(8*1024*1024+1));expected,_=hashes(path)
    ranges=[]
    class Session:
        def request(self,*args,**kwargs):
            return SimpleNamespace(status_code=200,headers={'Location':'https://www.googleapis.com/upload/drive/v3/files/fixed?upload_id=test'})
        def put(self,url,*,data,headers,**kwargs):
            ranges.append(headers['Content-Range'])
            if len(ranges)==1:raise TimeoutError()
            if len(ranges)==2:return SimpleNamespace(status_code=308,headers={'Range':'bytes=0-4194303'})
            return SimpleNamespace(status_code=200,headers={})
    class Drive:
        session=Session()
        def request(self,*args,**kwargs):
            return {'id':'fixed','size':str(expected['size']),'sha256Checksum':expected['sha256']}
    assert upload(Drive(),path,'fixed',{},expected)['id']=='fixed'
    assert ranges==['bytes 0-8388607/8388609','bytes */8388609','bytes 4194304-8388608/8388609']
