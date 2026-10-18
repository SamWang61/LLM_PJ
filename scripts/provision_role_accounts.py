"""Provision the six authorized role identities from files, never from web input.

Private credentials are read from a repository-external file (plain JSON or
Windows DPAPI). Reports contain identity/status only, never password material.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from migrate_email_role_logins import apply as migrate

AUTHORIZED = {'cashsam@gmail.com', 'jeff841117@gmail.com', 'chen2000401@gmail.com'}
ROLES = {'admin', 'customer'}


def private_file(path):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('Credentials file must be outside the repository')
    data = path.read_bytes()
    if path.suffix.lower() == '.dpapi':
        class Blob(ctypes.Structure):
            _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]
        source_buffer = ctypes.create_string_buffer(data)
        source = Blob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
        target = Blob()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
            raise RuntimeError('Private credentials file could not be unlocked')
        try:
            data = ctypes.string_at(target.pbData, target.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(target.pbData)
    return json.loads(data)


def validate(spec, credentials):
    accounts = spec.get('accounts', [])
    if (spec.get('schema_version') != 1 or spec.get('password_changes_enabled') is not False
            or set(spec.get('roles', [])) != ROLES or len(accounts) != 3
            or {a.get('email') for a in accounts} != AUTHORIZED
            or any(not isinstance(a.get('name'), str) or not 1 <= len(a['name']) <= 100 for a in accounts)):
        raise ValueError('Account manifest does not match the authorized three people')
    passwords = credentials.get('role_passwords', {})
    if (set(passwords) != ROLES
            or any(not isinstance(p, str) or not 8 <= len(p) <= 1024 for p in passwords.values())
            or passwords['admin'] == passwords['customer']):
        raise ValueError('Two distinct valid role credentials are required')
    return accounts, passwords


def new_user(account, role, password_hash, now):
    return {'_id': ObjectId(), 'schema_version': 4, 'display_name': account['name'],
        'email': account['email'], 'auth_provider': 'local', 'password_hash': password_hash,
        'firebase_uid': None, 'role': role, 'is_active': True, 'status': 'active',
        'preferences': {'category_ids': [], 'tags': [], 'budget_min': None, 'budget_max': None, 'updated_at': None},
        'member_level': 'basic', 'registered_at': now, 'first_recommendation_generated_at': None,
        'last_login_at': None, 'created_at': now, 'updated_at': now}


def preflight(db, spec, credentials):
    accounts, passwords = validate(spec, credentials)
    existing = list(db.users.find({'email': {'$in': sorted(AUTHORIZED)}}))
    pairs = [(u['email'], u['role']) for u in existing]
    if (len(set(pairs)) != len(pairs) or any(u.get('schema_version') != 4
            or u.get('auth_provider') != 'local' or u.get('synthetic_batch_id')
            or u.get('role') not in ROLES for u in existing)):
        raise ValueError('Existing identities are outside the authorized local account scope')
    return accounts, passwords


def provision(db, spec, credentials, *, transaction_runner=None):
    accounts, passwords = preflight(db, spec, credentials)
    migration = migrate(db)
    # Generate salt once per planned identity, outside any retried transaction.
    planned = {(a['email'], role): new_user(a, role, generate_password_hash(passwords[role]), datetime.now(timezone.utc))
               for a in accounts for role in sorted(ROLES)}

    def write(session):
        result = []
        for (email, role), created in planned.items():
            previous = db.users.find_one({'email': email, 'role': role}, session=session)
            if previous and (previous.get('auth_provider') != 'local' or previous.get('synthetic_batch_id')
                             or previous.get('schema_version') != 4):
                raise ValueError('Identity changed after preflight')
            if previous:
                uid = previous['_id']
                same_password = check_password_hash(previous['password_hash'], passwords[role])
                changed = not same_password or previous.get('status') != 'active' or previous.get('is_active') is not True
                if changed:
                    # Compare against the version read in this transaction.
                    guard = {'_id': uid, 'role': role, 'email': email, 'password_hash': previous['password_hash']}
                    update = {'status': 'active', 'is_active': True, 'updated_at': created['updated_at']}
                    if not same_password:
                        update['password_hash'] = created['password_hash']
                    if db.users.update_one(guard, {'$set': update}, session=session).matched_count != 1:
                        raise RuntimeError('Concurrent credential update detected')
                    db.auth_sessions.delete_many({'user_id': uid}, session=session)
                action = 'updated' if changed else 'unchanged'
            else:
                uid = db.users.insert_one(created, session=session).inserted_id
                action = 'created'
            result.append({'email': email, 'role': role, 'id': str(uid), 'action': action})
        return result

    if transaction_runner is None:
        with db.client.start_session() as session:
            rows = session.with_transaction(write)
    else:
        rows = transaction_runner(write)
    verified = list(db.users.find({'email': {'$in': sorted(AUTHORIZED)}}, {'_id': 1, 'email': 1, 'role': 1, 'status': 1, 'is_active': 1}))
    expected = {(a['email'], role) for a in accounts for role in ROLES}
    if len(verified) != 6 or {(u['email'], u['role']) for u in verified} != expected or any(
            u['status'] != 'active' or u['is_active'] is not True for u in verified):
        raise RuntimeError('Account readback failed')
    return {'status': 'passed', 'database': db.name, 'migration': migration,
            'role_identities': 6, 'accounts': rows, 'password_changes_enabled': False,
            'credentials_logged': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--credentials-file', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    credentials = private_file(args.credentials_file)
    spec = json.loads(args.manifest.read_bytes())
    uri = credentials.get('mongo_uri', '')
    if urlparse(uri).hostname != 'vibecart-ai-free.odqe25w.mongodb.net':
        raise ValueError('Unauthorized Atlas target')
    with MongoClient(uri, serverSelectionTimeoutMS=15000) as client:
        db = client.vibecart_ai
        preflight(db, spec, credentials)
        if args.apply:
            result = provision(db, spec, credentials)
        else:
            result = {'status': 'dry_run_passed', 'role_identities_planned': 6, 'writes': 0}
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__,
                          'message': 'Provisioning stopped; credentials omitted'}))
        raise SystemExit(1)
