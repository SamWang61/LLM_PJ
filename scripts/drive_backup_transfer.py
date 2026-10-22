"""Drive content transfers with stable IDs, bounded uploads and hash readback.

Callers must acquire the backup lock and verify owner-only isolation first.
No permission restoration, key upload or destination deletion is implemented here.
"""
import hashlib
import json
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from drive_backup_acl import DriveError, identifier, FILE_FIELDS, API
from drive_backup_payload import hashes

UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files'
FIELDS = FILE_FIELDS + ',appProperties,headRevisionId'
CHUNK = 8 * 1024 * 1024


def matches(metadata, expected):
    if metadata.get('trashed') or int(metadata.get('size', -1)) != expected['size']:
        return False
    comparisons = [('sha256Checksum', 'sha256'), ('md5Checksum', 'md5')]
    present = [(a, b) for a, b in comparisons if metadata.get(a)]
    return bool(present) and all(metadata[a] == expected[b] for a, b in present)


def readback(drive, file_id):
    return drive.request('GET', f'files/{identifier(file_id)}', params={'fields': FIELDS})


def validate_upload_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.netloc != 'www.googleapis.com'
            or not parsed.path.startswith('/upload/drive/v3/files') or parsed.fragment):
        raise DriveError('Unexpected resumable upload destination')
    return url


def acknowledged(response, size):
    if response.status_code in (200, 201):
        return size
    if response.status_code != 308:
        raise DriveError(f'Upload status HTTP {response.status_code}')
    value = response.headers.get('Range')
    if not value:
        return 0
    match = re.fullmatch(r'bytes=0-(\d+)', value)
    if not match or int(match[1]) >= size:
        raise DriveError('Invalid resumable acknowledgement')
    return int(match[1]) + 1


def upload(drive, path, file_id, metadata, expected, *, create=False, save_session=None):
    """Uncertain writes are resolved by readback, never blind create/retry."""
    path, file_id = Path(path), identifier(file_id)
    actual, _ = hashes(path)
    if actual != expected:
        raise ValueError('Staged payload changed')
    body = dict(metadata)
    if create:
        body['id'] = file_id
    elif 'parents' in body or 'id' in body:
        raise ValueError('Updates cannot relocate or replace objects')
    method, url = ('POST', UPLOAD) if create else ('PATCH', UPLOAD + '/' + file_id)
    params = {'fields': FIELDS}
    try:
        if expected['size'] <= 5 * 1024 * 1024:
            boundary = 'llmpj_' + uuid.uuid4().hex
            data = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode()
                    + json.dumps(body, ensure_ascii=False).encode('utf8')
                    + f'\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                    + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode())
            response = drive.session.request(method, url, params={**params, 'uploadType': 'multipart'},
                data=data, headers={'Content-Type': 'multipart/related; boundary=' + boundary},
                timeout=120, allow_redirects=False)
            if not 200 <= response.status_code < 300:
                raise DriveError(f'Multipart upload HTTP {response.status_code}')
        else:
            response = drive.session.request(method, url, params={**params, 'uploadType': 'resumable'},
                json=body, headers={'X-Upload-Content-Type': 'application/octet-stream',
                                    'X-Upload-Content-Length': str(expected['size'])},
                timeout=60, allow_redirects=False)
            if not 200 <= response.status_code < 300:
                raise DriveError(f'Upload session HTTP {response.status_code}')
            location = validate_upload_url(response.headers.get('Location', ''))
            if save_session: save_session(location)
            offset, failures = 0, 0
            with path.open('rb') as stream:
                while offset < expected['size']:
                    stream.seek(offset); data = stream.read(CHUNK)
                    try:
                        response = drive.session.put(location, data=data, headers={
                            'Content-Type': 'application/octet-stream',
                            'Content-Range': f'bytes {offset}-{offset+len(data)-1}/{expected["size"]}'},
                            timeout=120, allow_redirects=False)
                        if response.status_code in (429, 500, 502, 503, 504):
                            raise DriveError('Upload response requires status query')
                    except Exception:
                        failures += 1
                        if failures > 3: raise DriveError('Upload recovery limit exceeded') from None
                        response = drive.session.put(location, data=b'', headers={
                            'Content-Range': f'bytes */{expected["size"]}'}, timeout=60, allow_redirects=False)
                    new_offset = acknowledged(response, expected['size'])
                    if new_offset == offset:
                        failures += 1
                        if failures > 3: raise DriveError('Upload made no confirmed progress')
                    offset = new_offset
    except Exception as error:
        # A completed write can lose its response. Readback is the only success proof.
        try:
            result = readback(drive, file_id)
            if result.get('id') == file_id and matches(result, expected): return result
        except Exception:
            pass
        raise DriveError('Upload not verified; preserve the journal and isolation') from None
    result = readback(drive, file_id)
    if result.get('id') != file_id or not matches(result, expected):
        raise DriveError('Cloud payload hash or identity mismatch')
    return result


def download(drive, file_id, destination, expected, revision=None):
    destination = Path(destination)
    if destination.exists():
        actual, _ = hashes(destination)
        if all(actual[k] == value for k, value in expected.items()): return actual
        raise ValueError('Existing private download differs')
    path = f'files/{identifier(file_id)}'
    if revision: path += f'/revisions/{identifier(revision)}'
    response = drive.session.get(API + path, params={'alt': 'media'}, stream=True,
                                 timeout=120, allow_redirects=False)
    if response.status_code != 200:
        raise DriveError(f'Download HTTP {response.status_code}')
    temporary = destination.with_name(destination.name + '.partial')
    if temporary.exists(): raise ValueError('Inspect incomplete private download before resuming')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open('xb') as output:
        for block in response.iter_content(1024 * 1024): output.write(block)
    response.close()
    actual, _ = hashes(temporary)
    if any(actual[k] != v for k, v in expected.items()):
        raise DriveError('Downloaded cloud content hash mismatch')
    temporary.replace(destination)
    return actual


def generated_ids(drive, count):
    result = []
    while len(result) < count:
        size = min(1000, count - len(result))
        page = drive.request('GET', 'files/generateIds', params={'count': size, 'space': 'drive', 'type': 'files'})
        ids = [identifier(x) for x in page.get('ids', [])]
        if len(ids) != size or len(set(ids)) != size or set(ids) & set(result):
            raise DriveError('Generated IDs missing or duplicated')
        result.extend(ids)
    return result
