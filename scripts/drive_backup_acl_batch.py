"""Complete read-only permission batches, never batched permission mutations.

Drive files.list omits permissionDetails; use permissions.list for every item.
Each batch has at most 100 GETs, validates response IDs, and re-reads any failed
or paginated item with the ordinary complete permissions endpoint.
"""
from concurrent.futures import ThreadPoolExecutor
from email import policy
from email.parser import BytesParser
import json,re,threading,time,uuid
from urllib.parse import urlencode
from drive_backup_acl import DriveError,PERMISSION_FIELDS,identifier

BATCH='https://www.googleapis.com/batch/drive/v3'


def parse_response(content_type,content,ids):
    message=BytesParser(policy=policy.default).parsebytes(
        b'Content-Type: '+content_type.encode('ascii')+b'\r\nMIME-Version: 1.0\r\n\r\n'+content)
    if not message.is_multipart() or message.get_content_type()!='multipart/mixed' or message.defects:
        raise DriveError('Malformed permission batch response')
    result={}
    for part in message.iter_parts():
        cid=part.get('Content-ID','').strip('<>')
        if not cid.startswith('response-'):raise DriveError('Unrecognized batch response ID')
        key=cid[len('response-'):]
        if key not in ids or key in result or part.get_content_type()!='application/http' or part.defects:
            raise DriveError('Missing, duplicate or out-of-scope batch part')
        raw=part.get_payload(decode=True)
        if not isinstance(raw,bytes):raise DriveError('Invalid batch response body')
        head,sep,body=raw.partition(b'\r\n\r\n')
        if not sep:head,sep,body=raw.partition(b'\n\n')
        match=re.fullmatch(rb'HTTP/1\.[01] ([0-9]{3})(?: [^\r\n]*)?',head.splitlines()[0])
        if not sep or not match:raise DriveError('Invalid nested HTTP response')
        status=int(match[1])
        if status!=200:
            result[key]=None;continue
        try:data=json.loads(body)
        except (ValueError,UnicodeDecodeError):raise DriveError('Invalid permission JSON') from None
        if not isinstance(data,dict) or not isinstance(data.get('permissions'),list):
            raise DriveError('Missing full permission collection')
        result[key]=None if data.get('nextPageToken') else data['permissions']
    if result.keys()!=set(ids):raise DriveError('Incomplete permission batch')
    return result


def permissions_batch(drive,ids):
    ids=[identifier(x) for x in ids]
    if not 1<=len(ids)<=100 or len(set(ids))!=len(ids):raise ValueError('Batch needs 1 to 100 distinct IDs')
    boundary='acl_'+uuid.uuid4().hex
    query=urlencode({'fields':f'nextPageToken,permissions({PERMISSION_FIELDS})','pageSize':100,
                     'supportsAllDrives':'true','includePermissionsForView':'published'})
    body=b''
    for key in ids:
        body+=(f'--{boundary}\r\nContent-Type: application/http\r\nContent-ID: <{key}>\r\n\r\n'
               f'GET /drive/v3/files/{key}/permissions?{query} HTTP/1.1\r\nAccept: application/json\r\n\r\n').encode('ascii')
    body+=f'--{boundary}--\r\n'.encode('ascii')
    # The outer POST contains only GETs. Transport retries cannot mutate Drive.
    for attempt in range(4):
        try:
            response=drive.session.post(BATCH,data=body,headers={'Content-Type':'multipart/mixed; boundary='+boundary},
                timeout=90,allow_redirects=False)
        except Exception:
            if attempt==3:raise DriveError('Read-only permission batch transport failed') from None
            time.sleep(2**attempt);continue
        if response.status_code in (429,500,502,503,504) and attempt<3:
            response.close();time.sleep(2**attempt);continue
        if response.status_code!=200:
            status=response.status_code;response.close()
            raise DriveError(f'Permission batch HTTP {status}')
        try:result=parse_response(response.headers.get('Content-Type',''),response.content,ids)
        finally:response.close()
        for key,value in result.items():
            if value is None:result[key]=drive.permissions(key)
        return result
    raise DriveError('Permission batch retry budget exceeded')


def permissions_many(ids,drive_factory,workers=4):
    ids=list(ids)
    if len(set(ids))!=len(ids):raise ValueError('Duplicate ACL inventory IDs')
    groups=[ids[i:i+100] for i in range(0,len(ids),100)]
    lock=threading.Lock();next_start=[0.0]
    def one(group):
        # At most one new 100-call batch per second, with bounded overlap.
        with lock:
            start=max(time.monotonic(),next_start[0]);next_start[0]=start+1
        delay=start-time.monotonic()
        if delay>0:time.sleep(delay)
        return permissions_batch(drive_factory(),group)
    result={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index,group in enumerate(pool.map(one,groups),1):
            if result.keys() & group.keys():raise DriveError('Duplicate ACL batch output')
            result.update(group)
            if index%10==0:print(json.dumps({'phase':'full_acl_readback','objects':len(result)}),flush=True)
    if result.keys()!=set(ids):raise DriveError('Full ACL inventory incomplete')
    return result
