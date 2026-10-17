"""Prepare/activate/retire two explicit demo identities. Secrets only on stdin/DPAPI.

The reserved email suffix carries the enforced UTC expiry; no validator changes,
synthetic-member activation, or production stock/order writes are performed.
"""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
import copy
import json
import os
import sys
from urllib.parse import urlparse
import requests

from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash


def credentials():
    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]
    vault = Path(os.environ['LOCALAPPDATA']) / 'CodexPrivateBackups/REN-HANDOVER-20261018'
    raw = (vault / 'credentials.dpapi').read_bytes()
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None,
                                                  None, None, 0, ctypes.byref(target)):
        raise RuntimeError('Current-user DPAPI vault could not be unlocked')
    try:
        result = json.loads(ctypes.string_at(target.pbData, target.cbData))
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)
    return vault, result


def run(config):
    parsed = urlparse(config['mongo_uri'])
    if parsed.scheme != 'mongodb+srv' or parsed.hostname != 'vibecart-ai-free.odqe25w.mongodb.net':
        raise RuntimeError('Authorized production cluster required')
    mode = config['mode']
    if mode not in {'prepare', 'activate', 'verify', 'retire'}:
        raise RuntimeError('Unsupported demo action')
    vault, secret = credentials()
    cutoff = datetime.fromisoformat(secret['expires_at'])
    if mode in {'activate', 'verify'} and datetime.now(timezone.utc) >= cutoff:
        raise RuntimeError('Demo window has expired')
    manifest_path = vault / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'accounts': []}
    client = MongoClient(config['mongo_uri'], serverSelectionTimeoutMS=15000)
    db = client['vibecart_ai']
    report = {'database': db.name, 'mode': mode, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'expires_at': cutoff.isoformat(), 'credentials_logged': False, 'accounts': []}
    try:
        template = db.users.find_one({'synthetic_batch_id': 'sam-synthetic-20261005-v1'})
        if not template:
            raise RuntimeError('Validated synthetic schema template unavailable')
        for entry in secret['accounts']:
            email = entry['email'].lower()
            expected_role = {'REN': 'customer', 'JEFF': 'admin'}.get(entry['holder'])
            if entry['role'] != expected_role or not email.endswith('-20261018t123000z@demo.vibecart.invalid'):
                raise RuntimeError('Demo identity scope mismatch')
            previous = next((r for r in manifest['accounts'] if r['holder'] == entry['holder']), None)
            existing = db.users.find_one({'email': email})
            if existing:
                if (not previous or str(existing['_id']) != previous['id']
                        or existing['role'] != expected_role
                        or not check_password_hash(existing['password_hash'], entry['password'])):
                    raise RuntimeError('Existing identity is not this handover account; refusing overwrite')
                uid = existing['_id']
            else:
                if mode != 'prepare' or previous:
                    raise RuntimeError('Prepared account missing; refusing implicit creation')
                now = datetime.now(timezone.utc)
                row = copy.deepcopy(template)
                for field in ('synthetic_batch_id', 'demographics', 'name'):
                    row.pop(field, None)
                uid = ObjectId()
                row.update(_id=uid, email=email, display_name=entry['holder'] + ' 展示帳號',
                    password_hash=generate_password_hash(entry['password']), role=expected_role,
                    status='inactive', is_active=False, auth_provider='local', firebase_uid=None,
                    registered_at=now, first_recommendation_generated_at=None, last_login_at=None,
                    created_at=now, updated_at=now,
                    preferences={'category_ids': [], 'tags': ['demo'], 'budget_min': None,
                                 'budget_max': None, 'updated_at': None})
                db.users.insert_one(row)
                manifest['accounts'].append({'holder': entry['holder'], 'id': str(uid),
                                             'role': expected_role, 'email': email})
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            if mode in {'activate', 'retire'}:
                active = mode == 'activate'
                db.users.update_one({'_id': uid, 'email': email}, {'$set': {
                    'status': 'active' if active else 'inactive', 'is_active': active,
                    'updated_at': datetime.now(timezone.utc)}})
            if mode in {'prepare', 'retire'}:
                db.auth_sessions.delete_many({'user_id': uid})
            checked = db.users.find_one({'_id': uid})
            verification = {}
            if mode == 'verify':
                base = 'https://vibecart-llmai.web.app'
                before = {r['_id'] for r in db.auth_sessions.find({'user_id': uid}, {'_id': 1})}
                browser = requests.Session()
                try:
                    from bs4 import BeautifulSoup
                    response = browser.get(base + '/auth/login', timeout=30)
                    field = BeautifulSoup(response.text, 'html.parser').select_one('input[name="csrf_token"]')
                    if response.status_code != 200 or not field:
                        raise RuntimeError('Demo login form unavailable')
                    response = browser.post(base + '/auth/login', data={
                        'email': email, 'password': entry['password'], 'csrf_token': field['value']},
                        allow_redirects=False, timeout=30)
                    if response.status_code not in (302, 303):
                        raise RuntimeError('Demo login failed')
                    cart = browser.get(base + '/cart', allow_redirects=False, timeout=30)
                    admin = browser.get(base + '/admin/', allow_redirects=False, timeout=30)
                    allowed = expected_role == 'admin'
                    if cart.status_code != 200 or (admin.status_code == 200) != allowed:
                        raise RuntimeError('Demo role verification failed')
                    if not allowed and admin.status_code not in (302, 303):
                        raise RuntimeError('Customer admin rejection missing')
                    verification = {'login_http': response.status_code, 'cart_http': cart.status_code,
                                    'admin_http': admin.status_code, 'role_verified': True,
                                    'production_checkout_performed': False}
                finally:
                    after = {r['_id'] for r in db.auth_sessions.find({'user_id': uid}, {'_id': 1})}
                    own = list(after - before)
                    if own:
                        db.auth_sessions.delete_many({'user_id': uid, '_id': {'$in': own}})
                    browser.close()
            report['accounts'].append({'holder': entry['holder'], 'role': expected_role,
                'id': str(uid), 'active': checked['is_active'],
                'sessions': db.auth_sessions.count_documents({'user_id': uid}), **verification})
        report['status'] = 'passed'
        return report
    finally:
        client.close()


if __name__ == '__main__':
    try:
        print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__,
                          'error': str(error) if isinstance(error, RuntimeError) else 'Demo action failed'}))
        raise SystemExit(1)
