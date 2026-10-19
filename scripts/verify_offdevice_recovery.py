"""N14: authenticate two private backup archives on a different Windows PC.

Requires the base ciphertext, latest delta/Atlas ciphertext, and separately
carried 32-byte recovery key. Never contacts production or Atlas. Optional
--mongod restores the snapshot to a disposable localhost-only database.
Outputs remain private under a new destination directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import time
from uuid import uuid4
import zipfile

from encrypted_backup import decrypt
from source_snapshot_delta import restore_delta, safe_name

BASE_CIPHER_SHA256 = '328b9aa8194589d53d8f18e7d41b0e96809335a1329bd23ed3ba95d992fe51d5'
LATEST_CIPHER_SHA256 = '5ff28ee49341fa6070ab6b1e418106ed8623901071b3d4e3d54c7c97092aa885'
BASE_ZIP_SHA256 = '75f91fcf4b490a112ec1672393600d7cab5c649e60282d9f1203cc3516d9a291'
LATEST_ZIP_SHA256 = '26e99a399c442e2b41d846e06fe6065c7045e81f42f65e8645227d53eba2b53a'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_extract(archive_path, destination):
    destination.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        names = [row.filename for row in archive.infolist()]
        require(len(names) == len(set(x.casefold() for x in names)), 'Duplicate archive path')
        for row in archive.infolist():
            name = safe_name(row.filename)
            require(not stat.S_ISLNK(row.external_attr >> 16) and not name.endswith('/'),
                    'Unsafe archive member')
            target = destination / name
            require(target.resolve().is_relative_to(destination.resolve()), 'Archive path escaped destination')
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(row) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
    return len(names)


def restore_local_database(mongod, snapshot, destination):
    from pymongo import MongoClient
    binary = Path(mongod).resolve(strict=True)
    require(binary.name.lower() == 'mongod.exe' and binary.is_file(), 'mongod.exe required')
    data = destination / 'disposable-mongo-data'
    data.mkdir()
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1', 0))
        port = reserved.getsockname()[1]
    name = 'sam_n14_restore_' + uuid4().hex
    log = destination / 'disposable-mongod.log'
    command = [str(binary), '--bind_ip', '127.0.0.1', '--port', str(port),
               '--dbpath', str(data), '--logpath', str(log),
               '--setParameter', 'ttlMonitorEnabled=false']
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    process = subprocess.Popen(command, creationflags=flags)
    client = None
    restored = None
    cleaned = False
    try:
        client = MongoClient(f'mongodb://127.0.0.1:{port}/?directConnection=true',
                             serverSelectionTimeoutMS=1000)
        for _ in range(45):
            try:
                if client.admin.command('ping').get('ok') == 1:
                    break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Disposable localhost mongod did not start')
        from atlas_snapshot_backup import restore_snapshot
        restored = restore_snapshot(client, name, snapshot)
        require(restored['verified'] and restored['raw_bson_hash_differences'] == 0,
                'Database restoration mismatch')
        client.drop_database(name)
        require(name not in client.list_database_names(), 'Disposable database cleanup failed')
        cleaned = True
    finally:
        if client is not None:
            client.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    require(cleaned and process.poll() is not None, 'Disposable mongod cleanup failed')
    return { 'verified': True, 'collections': restored['collections'],
             'documents': restored['documents'], 'indexes': restored['indexes'],
             'ttl_indexes': restored['ttl_indexes'], 'validators_and_index_options_equal': True,
             'raw_bson_hash_differences': 0, 'source_database_contacted': False,
             'disposable_database_removed': cleaned, 'disposable_process_stopped': True,
             'target_version': restored['target_version'] }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ciphertext', required=True, type=Path)
    parser.add_argument('--latest-ciphertext', required=True, type=Path)
    parser.add_argument('--key-file', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--mongod', type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    require(not destination.exists(), 'Destination must be new and private')
    for source in (args.base_ciphertext, args.latest_ciphertext, args.key_file):
        require(source.is_absolute() and not source.is_symlink(), 'Absolute, non-link inputs required')
    require(args.key_file.stat().st_size == 32, 'Recovery key must be exactly 32 bytes')
    require(sha256(args.base_ciphertext) == BASE_CIPHER_SHA256, 'Base ciphertext SHA-256 mismatch')
    require(sha256(args.latest_ciphertext) == LATEST_CIPHER_SHA256, 'Latest ciphertext SHA-256 mismatch')
    require(not destination.is_relative_to(args.base_ciphertext.parent.resolve())
            and not destination.is_relative_to(args.latest_ciphertext.parent.resolve()),
            'Destination cannot be on the backup media')
    destination.mkdir(parents=True)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'failed',
              'computer_name': os.environ.get('COMPUTERNAME'), 'source_database_contacted': False,
              'base_ciphertext_sha256': BASE_CIPHER_SHA256,
              'latest_ciphertext_sha256': LATEST_CIPHER_SHA256}
    try:
        base_zip, latest_zip = destination / 'base.zip', destination / 'latest.zip'
        base = decrypt(args.base_ciphertext, base_zip, args.key_file)
        latest = decrypt(args.latest_ciphertext, latest_zip, args.key_file)
        require(base['plaintext']['sha256'] == BASE_ZIP_SHA256
                and latest['plaintext']['sha256'] == LATEST_ZIP_SHA256,
                'Authenticated ZIP hash mismatch')
        report['authenticated_decryption'] = True
        capsule = destination / 'capsule'
        report['capsule_files'] = safe_extract(latest_zip, capsule)
        source = destination / 'restored-source'
        report['source'] = restore_delta(base_zip,
            capsule / 'source' / 'latest-source-delta.zip', source)
        if args.mongod:
            report['database'] = restore_local_database(args.mongod,
                capsule / 'atlas-snapshot', destination)
        else:
            report['database'] = {'verified': False, 'reason': 'mongod not supplied'}
        report['status'] = 'passed' if report['database']['verified'] else 'source-only-passed'
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['error'] = str(error) if isinstance(error, ValueError) else 'See private local log'
    finally:
        (destination / 'recovery-report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('source', 'database')},
                     ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
