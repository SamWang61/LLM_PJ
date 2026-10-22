import json
from types import SimpleNamespace
import pytest
import drive_backup_acl_batch as batch
from drive_backup_acl import DriveError


def response(rows):
    boundary='test_boundary';parts=[]
    for key,status,data in rows:
        parts.append((f'--{boundary}\r\nContent-Type: application/http\r\nContent-ID: <response-{key}>\r\n\r\n'
                      f'HTTP/1.1 {status} Status\r\nContent-Type: application/json\r\n\r\n').encode()
                     +json.dumps(data,ensure_ascii=False).encode('utf8')+b'\r\n')
    return 'multipart/mixed; boundary='+boundary,b''.join(parts)+f'--{boundary}--\r\n'.encode()


def test_unicode_response_is_matched_by_id_not_order():
    rows=[('b',200,{'permissions':[{'id':'u','displayName':'仁千'}]}),('a',200,{'permissions':[]})]
    result=batch.parse_response(*response(rows),['a','b'])
    assert result=={'b':[{'id':'u','displayName':'仁千'}],'a':[]}


@pytest.mark.parametrize('rows',[
    [('a',200,{'permissions':[]})],
    [('a',200,{'permissions':[]}),('a',200,{'permissions':[]})],
    [('a',200,{'permissions':[]}),('outside',200,{'permissions':[]})],
    [('a',200,{}),('b',200,{'permissions':[]})],
])
def test_incomplete_duplicate_unknown_or_malformed_acl_never_counts_as_success(rows):
    with pytest.raises(DriveError):batch.parse_response(*response(rows),['a','b'])


def test_failed_parts_and_pagination_fall_back_to_complete_read_only_endpoint():
    kind,content=response([('a',503,{}),('b',200,{'permissions':[],'nextPageToken':'next'})])
    posts=[];reads=[]
    def post(url,**kwargs):
        posts.append((url,kwargs));return SimpleNamespace(status_code=200,headers={'Content-Type':kind},content=content,close=lambda:None)
    def permissions(key):reads.append(key);return [{'id':key,'role':'owner'}]
    api=SimpleNamespace(session=SimpleNamespace(post=post),permissions=permissions)
    result=batch.permissions_batch(api,['a','b'])
    assert reads==['a','b'] and set(result)=={'a','b'}
    url,options=posts[0]
    assert url==batch.BATCH and options['allow_redirects'] is False
    assert options['data'].count(b'GET /drive/v3/files/')==2
    assert b'POST /' not in options['data'] and b'DELETE /' not in options['data']


@pytest.mark.parametrize('ids',[[],['a','a'],['../escape'],[f'item{i}' for i in range(101)]])
def test_invalid_batch_cannot_make_network_calls(ids):
    with pytest.raises(ValueError):batch.permissions_batch(None,ids)


def test_outer_retry_is_bounded_and_contains_only_gets(monkeypatch):
    calls=[]
    def post(*args,**kwargs):
        calls.append(kwargs['data'])
        return SimpleNamespace(status_code=429,close=lambda:None)
    api=SimpleNamespace(session=SimpleNamespace(post=post))
    monkeypatch.setattr(batch.time,'sleep',lambda _:None)
    with pytest.raises(DriveError,match='429'):batch.permissions_batch(api,['a'])
    assert len(calls)==8 and len(set(calls))==1


def test_outer_403_quota_retries_read_only_batch(monkeypatch):
    kind,content=response([('a',200,{'permissions':[{'id':'owner','role':'owner'}]})])
    calls=[];waits=[]
    def post(url,**kwargs):
        calls.append(kwargs['data'])
        if len(calls)==1:
            return SimpleNamespace(status_code=403,json=lambda:{'error':{'errors':[{'reason':'rateLimitExceeded'}]}},close=lambda:None)
        return SimpleNamespace(status_code=200,headers={'Content-Type':kind},content=content,close=lambda:None)
    api=SimpleNamespace(session=SimpleNamespace(post=post))
    monkeypatch.setattr(batch.time,'sleep',waits.append)
    assert batch.permissions_batch(api,['a'])=={'a':[{'id':'owner','role':'owner'}]}
    assert len(calls)==2 and calls[0]==calls[1] and len(waits)==1


def test_outer_permission_denial_is_not_retried(monkeypatch):
    calls=[]
    def post(*args,**kwargs):
        calls.append(True)
        return SimpleNamespace(status_code=403,json=lambda:{'error':{'errors':[{'reason':'insufficientFilePermissions'}]}},close=lambda:None)
    monkeypatch.setattr(batch.time,'sleep',lambda _:pytest.fail('Unexpected permission retry'))
    with pytest.raises(DriveError,match='403'):
        batch.permissions_batch(SimpleNamespace(session=SimpleNamespace(post=post)),['a'])
    assert len(calls)==1


def test_batch_tls_failure_is_not_retried(monkeypatch):
    from requests.exceptions import SSLError
    def post(*args,**kwargs):raise SSLError('private')
    monkeypatch.setattr(batch.time,'sleep',lambda _:pytest.fail('Unexpected TLS retry'))
    with pytest.raises(DriveError,match='TLS validation'):
        batch.permissions_batch(SimpleNamespace(session=SimpleNamespace(post=post)),['a'])


def test_permission_batches_leave_quota_headroom_and_include_every_id(monkeypatch):
    clock=[0.0];starts=[]
    monkeypatch.setattr(batch.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(batch.time,'sleep',lambda delay:clock.__setitem__(0,clock[0]+delay))
    def one(api,ids):
        starts.append(clock[0])
        return {key:[{'id':'owner','role':'owner'}] for key in ids}
    monkeypatch.setattr(batch,'permissions_batch',one)
    ids=[f'file_{i}' for i in range(250)]
    result=batch.permissions_many(ids,lambda:None,workers=1)
    assert set(result)==set(ids) and starts==[0.0,3.0,6.0]
