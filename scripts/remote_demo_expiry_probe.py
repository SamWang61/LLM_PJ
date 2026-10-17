"""Short-lived identity expiry on private HTTP, with no production writes."""
import json
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from remote_d4_consumer_probe import verify_scope, verify_database_roles, require
from remote_account_acceptance_probe import browser, sign_in, protected, cleanup


def run(config):
    verify_scope(config)
    client = MongoClient(config['mongo_uri'], serverSelectionTimeoutMS=15000)
    db = client['vibecart_acceptance_pr21']
    verify_database_roles(client)
    uid, marker = ObjectId(), 'sam-accounts-expiry-' + secrets.token_hex(8)
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(seconds=20)).replace(microsecond=0)
    email = marker + '-' + cutoff.strftime('%Y%m%dt%H%M%Sz') + '@demo.vibecart.invalid'
    password = secrets.token_urlsafe(24)
    report = {'status': 'failed', 'probe_id': marker, 'cutoff': cutoff.isoformat(),
              'source': 'private real HTTP clock expiry; no production account modified'}
    try:
        db.users.insert_one({'_id': uid, 'schema_version': 4, 'status': 'active',
            'is_active': True, 'role': 'customer', 'email': email,
            'display_name': 'Private expiry fixture', 'password_hash': generate_password_hash(password),
            'created_at': now, 'updated_at': now, 'acceptance_run': marker})
        base = config['service_url'].rstrip('/')
        session = browser(config['id_token'])
        sign_in(session, base, email, password)
        protected(session, base, '/cart', allowed=True)
        require(datetime.now(timezone.utc) < cutoff, 'Fixture expired before initial verification')
        time.sleep(max(0, (cutoff - datetime.now(timezone.utc)).total_seconds()) + 1)
        protected(session, base, '/cart', allowed=False)
        fresh = browser(config['id_token'])
        sign_in(fresh, base, email, password, enabled=False)
        protected(fresh, base, '/cart', allowed=False)
        require(db.users.find_one({'_id': uid})['is_active'], 'Expiry test used account disable')
        report.update(status='passed', checked_at=datetime.now(timezone.utc).isoformat(),
            before_cutoff_access=True, after_cutoff_existing_cookie_denied=True,
            after_cutoff_new_login_denied=True, account_still_active_during_test=True)
    except Exception as error:
        report['error'] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
    finally:
        report['cleanup'] = cleanup(db, marker, [uid])
        if not report['cleanup']['verified']:
            report['status'] = 'cleanup_failed'
        client.close()
    print(json.dumps(report))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(run(json.load(sys.stdin)))
