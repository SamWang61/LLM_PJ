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
    assert len(calls)==4 and len(set(calls))==1
