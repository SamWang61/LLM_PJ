"""Real local MongoDB: role index, strict validators and all-six atomic writes."""
from flask import g
import pytest

from app import create_app
from scripts.provision_role_accounts import provision
from schema_active_v4 import SCHEMAS
from test_ren_transactions import replica
from test_dual_role_login import SPEC, SECRETS
from test_ren_auth_order import login


def prepare(db):
    db.users.delete_many({})
    db.command('collMod', 'users', validator=SCHEMAS['users'], validationLevel='strict', validationAction='error')
    db.users.create_index('email', unique=True, name='uq_users_email')
    for name in ['auth_sessions', 'schema_migrations']:
        db.create_collection(name, validator=SCHEMAS[name], validationLevel='strict', validationAction='error')


def test_six_valid_roles_authenticate_with_real_index_and_sessions(replica):
    db, _, _, _ = replica
    prepare(db)
    result = provision(db, SPEC, SECRETS)
    assert result['role_identities'] == 6
    assert db.users.count_documents(SCHEMAS['users']) == 6
    assert db.users.count_documents({'email': 'cashsam@gmail.com'}) == 2
    app = create_app({'TESTING': True, 'SECRET_KEY': 'local-role-test-only', 'DATA_MODE': 'v4'})

    @app.before_request
    def local_db():
        g.db = db

    for account in SPEC['accounts']:
        for role in ['customer', 'admin']:
            browser = app.test_client()
            assert login(browser, account['email'], SECRETS['role_passwords'][role]).status_code == 302
            with browser.session_transaction() as state:
                assert state['role'] == role
                uid = state['user_id']
            assert (browser.get('/admin/').status_code == 200) is (role == 'admin')
            browser.get('/auth/logout')
            with browser.session_transaction() as state:
                csrf = state['csrf_token']
            assert browser.post('/auth/logout', data={'csrf_token': csrf}).status_code == 302
    assert db.auth_sessions.count_documents({}) == 0
    assert all(r['action'] == 'unchanged' for r in provision(db, SPEC, SECRETS)['accounts'])


def test_failure_after_six_account_writes_rolls_every_account_back(replica):
    db, _, _, _ = replica
    prepare(db)

    def transaction(callback):
        with db.client.start_session() as session:
            def fail(active):
                callback(active)
                raise RuntimeError('after-all-six-writes')
            return session.with_transaction(fail)

    with pytest.raises(RuntimeError, match='after-all-six-writes'):
        provision(db, SPEC, SECRETS, transaction_runner=transaction)
    assert db.users.count_documents({}) == 0
    assert db.auth_sessions.count_documents({}) == 0
    assert provision(db, SPEC, SECRETS)['role_identities'] == 6
