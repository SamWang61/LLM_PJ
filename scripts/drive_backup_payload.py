"""Private, complete source manifests and authenticated per-file payloads.

No cloud mutations. Exclusions must be explicitly approved outside this module.
Credential values are never emitted. The encryption key stays outside payloads.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import zipfile
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from encrypted_backup import encrypt, decrypt, fingerprint, stamp
from drive_backup_acl import write_private_json

PRIVATE_TREES = {'.git', '.codex', '.backup-state'}
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.dpapi', '.sqlite', '.sqlite3', '.db',
                    '.zip', '.7z', '.rar', '.tar', '.gz', '.bak', '.doc', '.xls'}
PATTERNS = [re.compile(x, re.I) for x in (
    rb'mongodb(?:\+srv)?://([^\s:/]+):([^\s@/]+)@',
    rb'gh[pousr]_[a-z0-9]{30,}', rb'github_pat_[a-z0-9_]{40,}',
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'AKIA[0-9A-Z]{16}', rb'sk-ant-[a-z0-9_-]{20,}',
    rb'ya29\.[a-z0-9_-]{20,}', rb'"refresh_token"\s*:\s*"[^"<>]{15,}"',
    rb'"private_key"\s*:\s*"-----BEGIN',
)]
MARKERS = [(b'mongodb',), (b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_'),
           (b'github_pat_',), (b'-----begin',), (b'akia',), (b'sk-ant-',),
           (b'ya29.',), (b'"refresh_token"',), (b'"private_key"',)]


def safe_relative(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '\\' in value or ':' in value
            or any(p in {'', '.', '..'} for p in value.split('/'))):
        raise ValueError('Unsafe relative path')
    return path


def sensitive_name(relative):
    path = safe_relative(relative)
    name = path.name.lower()
    return (path.parts[0] in PRIVATE_TREES
            or (name.startswith('.env') and name != '.env.example')
            or name.startswith('client_secret')
            or any(x in name for x in ('credential', 'service_account', 'service-account', 'firebase-adminsdk'))
            or path.suffix.lower() in PRIVATE_SUFFIXES)


def secret_bytes(data):
    lowered = data.lower()
    for pattern, markers in zip(PATTERNS, MARKERS):
        if not any(marker in lowered for marker in markers):
            continue
        for match in pattern.finditer(data):
            if pattern is PATTERNS[0]:
                # Placeholder examples remain readable; actual strings are never logged.
                if all(re.fullmatch(rb'(?:<[^<>]+>|\$\{[^{}]+\})', value)
                       for value in match.groups()):
                    continue
            return True
    return False


def scan(root, excludes=()):
    root = Path(root).resolve(strict=True)
    exclusions = {str(safe_relative(x)) for x in excludes}
    files, directories, errors = {}, [], []
    queue = [root]
    while queue:
        directory = queue.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    if any(relative == x or relative.startswith(x + '/') for x in exclusions):
                        continue
                    if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                        errors.append({'path': relative, 'error': 'link_requires_policy'})
                    elif entry.is_dir(follow_symlinks=False):
                        directories.append(relative); queue.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        stat = entry.stat(follow_symlinks=False)
                        files[relative] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        except OSError as error:
            errors.append({'path': directory.relative_to(root).as_posix(), 'error': type(error).__name__})
    return {'root': str(root), 'files': files, 'directories': sorted(directories),
            'exclusions': sorted(exclusions), 'errors': errors, 'complete': not errors}


def hashes(path, detect=False):
    before = path.stat()
    sha, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    detected, tail = False, b''
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(block); md5.update(block)
            if detect and not detected:
                detected = secret_bytes(tail + block)
                tail = block[-4096:]
    if stamp(before) != stamp(path.stat()):
        raise ValueError('Source changed while reading')
    return {'size': before.st_size, 'sha256': sha.hexdigest(), 'md5': md5.hexdigest()}, detected


def office_secret(path):
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            if reader.is_encrypted:
                return True
            return any(secret_bytes((page.extract_text() or '').encode('utf8')) for page in reader.pages)
        except Exception:
            return True
    if path.suffix.lower() not in {'.docx', '.xlsx', '.pptx', '.docm', '.xlsm', '.pptm'}:
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if item.file_size > 64 * 1024 * 1024:
                    return True  # Unbounded content remains encrypted, not silently skipped.
                if secret_bytes(archive.read(item)):
                    return True
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return True
    return False


def prepare(root, directory, key, excludes=(), workers=8, stage_readable_only=False):
    root, directory, key = Path(root).resolve(), Path(directory).resolve(), Path(key).resolve()
    if directory.is_relative_to(root) or key.is_relative_to(root) or key.is_relative_to(directory):
        raise ValueError('Keep private staging and key separate from source and each other')
    directory.mkdir(exist_ok=False)
    listing = scan(root, excludes)
    write_private_json(directory / 'source-listing.json', listing)
    if not listing['complete'] and not stage_readable_only:
        raise ValueError('Source cannot be completely read; no payload is ready')
    staged = directory / 'source'; payloads = directory / 'payloads'; restored = directory / 'restore-check'
    for p in (staged, payloads, restored): p.mkdir()
    def one(relative):
        source = root / relative
        target = staged / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = source.stat()
        expected = listing['files'][relative]
        if (before.st_size, before.st_mtime_ns) != (expected['size'], expected['mtime_ns']):
            raise ValueError('Source changed before snapshot')
        shutil.copyfile(source, target)
        if stamp(before) != stamp(source.stat()):
            raise ValueError('Source changed during snapshot')
        plain, content_secret = hashes(target, detect=not sensitive_name(relative))
        encrypted = sensitive_name(relative) or content_secret or office_secret(target)
        payload = target
        if encrypted:
            payload = payloads / relative
            payload.parent.mkdir(parents=True, exist_ok=True)
            encrypt(target, payload, key)
            check = restored / relative
            check.parent.mkdir(parents=True, exist_ok=True)
            result = decrypt(payload, check, key)
            if result['plaintext']['sha256'] != plain['sha256']:
                raise ValueError('Authenticated local recovery mismatch')
            check.unlink()  # Our verified temporary plaintext only, inside private staging.
        outgoing, _ = hashes(payload)
        return relative, {'plaintext': plain, 'payload': outgoing, 'encrypted': encrypted,
                          'payload_path': str(payload), 'source_mtime_ns': before.st_mtime_ns}
    records = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, (relative, record) in enumerate(pool.map(one, listing['files']), 1):
            records[relative] = record
            if index % 2000 == 0:
                print(json.dumps({'phase': 'prepared_files', 'count': index}), flush=True)
    if listing['complete']:
        verify_source(root, {'files': records, 'directories': listing['directories'], 'exclusions': listing['exclusions']})
    manifest = {'schema': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
                'source_root': str(root), 'files': records, 'directories': listing['directories'],
                'exclusions': listing['exclusions'], 'complete': listing['complete'],
                'source_errors': listing['errors'],
                'key_id': hashlib.sha256(key.read_bytes()).hexdigest()[:16]}
    write_private_json(directory / 'manifest.json', manifest)
    return manifest


def verify_source(root, manifest, workers=8):
    current = scan(root, manifest['exclusions'])
    if (not current['complete'] or current['files'].keys() != manifest['files'].keys()
            or current['directories'] != manifest['directories']):
        raise ValueError('Source tree changed or is unreadable')
    def one(relative):
        actual, _ = hashes(Path(root) / relative)
        if actual != manifest['files'][relative]['plaintext']:
            raise ValueError('Source content changed')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, manifest['files']))
    return {'complete': True, 'files': len(manifest['files']), 'checked_at': datetime.now(timezone.utc).isoformat()}
