"""Same-email role selection uses passwords and independent database identities."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from test_v4_routes import shop
from test_ren_auth_order import login, cookie, replay
from scripts.provision_role_accounts import provision, preflight, new_user, AUTHORIZED

ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((ROOT / 'config/role_accounts_20261018.json').read_bytes())
# Deliberately unrelated to real classroom credentials.
SECRETS = {'role_passwords': {'customer': 'test-customer-password-only', 'admin': 'test-admin-password-only'}}


@pytest.fixture
def dual(shop):
    app, browser, db, uid, pid, sid = shop
    db.users.create_index('email', unique=True, name='uq_users_email')
    result = provision(db, SPEC, SECRETS, transaction_runner=lambda f: f(None))
    assert result['role_identities'] == 6
    return app, db


@pytest.mark.parametrize('email', sorted(AUTHORIZED))
@pytest.mark.parametrize('role', ['customer', 'admin'])
def test_each_password_selects_the_requested_role_and_landing(dual, email, role):
    app, db = dual
    browser = app.test_client()
    result = login(browser, email, SECRETS['role_passwords'][role])
    assert result.status_code == 302
    assert result.location == ('/admin/' if role == 'admin' else '/')
    with browser.session_transaction() as state:
        assert state['role'] == role
        assert state['user_id'] == str(db.users.find_one({'email': email, 'role': role})['_id'])
    assert (browser.get('/admin/').status_code == 200) is (role == 'admin')


def test_posted_role_cannot_promote_and_switching_retires_only_prior_device(dual):
    app, db = dual
    email = 'cashsam@gmail.com'
    first, other = app.test_client(), app.test_client()
    assert login(first, email, SECRETS['role_passwords']['customer']).status_code == 302
    old = cookie(first)
    assert login(other, email, SECRETS['role_passwords']['customer']).status_code == 302
    other_cookie = cookie(other)
    first.get('/auth/login')
    with first.session_transaction() as state:
        csrf = state['csrf_token']
    assert first.post('/auth/login', data={'csrf_token': csrf, 'email': email, 'role': 'admin',
        'password': SECRETS['role_passwords']['customer']}).location == '/'
    assert first.get('/admin/').status_code == 302
    assert login(first, email, SECRETS['role_passwords']['admin']).location == '/admin/'
    assert replay(app, old).get('/cart').status_code == 302
    assert replay(app, other_cookie).get('/cart').status_code == 200
    assert first.get('/admin/').status_code == 200


def test_ambiguous_password_and_disabled_role_fail_closed(dual):
    app, db = dual
    email = 'cashsam@gmail.com'
    browser = app.test_client()
    db.users.update_one({'email': email, 'role': 'admin'}, {'$set': {'status': 'inactive', 'is_active': False}})
    assert login(browser, email, SECRETS['role_passwords']['admin']).status_code == 200
    assert browser.get('/cart').status_code == 302
    assert login(browser, email, SECRETS['role_passwords']['customer']).location == '/'
    db.users.update_one({'email': email, 'role': 'admin'}, {'$set': {
        'status': 'active', 'is_active': True,
        'password_hash': generate_password_hash(SECRETS['role_passwords']['customer'])}})
    anonymous = app.test_client()
    assert login(anonymous, email, SECRETS['role_passwords']['customer']).status_code == 200
    assert anonymous.get('/cart').status_code == 302


@pytest.mark.parametrize('role', ['customer', 'admin'])
def test_password_changes_blocked_without_writing_any_credentials(dual, role):
    app, db = dual
    browser = app.test_client()
    assert login(browser, 'cashsam@gmail.com', SECRETS['role_passwords'][role]).status_code == 302
    browser.get('/auth/login')
    before = list(db.users.find({}))
    with browser.session_transaction() as state:
        csrf = state['csrf_token']
    assert browser.get('/auth/password').status_code == 403
    assert browser.post('/auth/password', data={'csrf_token': csrf, 'password': 'a-new-test-password'}).status_code == 403
    assert list(db.users.find({})) == before


def test_provisioning_is_idempotent_preserves_other_data_and_never_logs_secrets(dual):
    app, db = dual
    before = list(db.users.find({}))
    sessions = list(db.auth_sessions.find({}))
    result = provision(db, SPEC, SECRETS, transaction_runner=lambda f: f(None))
    assert all(r['action'] == 'unchanged' for r in result['accounts'])
    assert list(db.users.find({})) == before
    assert list(db.auth_sessions.find({})) == sessions
    assert not any(value in json.dumps(result) for value in SECRETS['role_passwords'].values())
    assert 'password_hash' not in json.dumps(result)
    for account in SPEC['accounts']:
        for role in ['admin', 'customer']:
            row = db.users.find_one({'email': account['email'], 'role': role})
            assert check_password_hash(row['password_hash'], SECRETS['role_passwords'][role])
            with pytest.raises(DuplicateKeyError):
                db.users.insert_one({**row, '_id': 'different-id'})


def test_preflight_rejects_scope_and_synthetic_identity_without_writes(shop):
    _, _, db, _, _, _ = shop
    invalid = copy.deepcopy(SPEC)
    invalid['accounts'][1]['email'] = 'wrong@example.test'
    with pytest.raises(ValueError):
        preflight(db, invalid, SECRETS)
    synthetic = new_user(SPEC['accounts'][0], 'admin', generate_password_hash('old-test-only'), datetime.now(timezone.utc))
    synthetic['synthetic_batch_id'] = 'must-remain-disabled'
    synthetic.update(status='inactive', is_active=False)
    db.users.insert_one(synthetic)
    before = list(db.users.find({}))
    with pytest.raises(ValueError):
        provision(db, SPEC, SECRETS, transaction_runner=lambda f: f(None))
    assert list(db.users.find({})) == before
    assert db.schema_migrations.count_documents({}) == 0
