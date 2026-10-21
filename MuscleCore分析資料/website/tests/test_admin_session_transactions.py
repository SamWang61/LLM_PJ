"""Actual MongoDB transaction/validator tests in the owned localhost replica only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4
import pytest
from bson import ObjectId
from pymongo.errors import OperationFailure, PyMongoError
from test_ren_transactions import replica
from app.services.admin_sessions import AdminSessionService, CartConflict, MIGRATION, RETENTION_SECONDS, utcnow

ROOT = Path(__file__).resolve().parents[3]
spec = spec_from_file_location('migrate_customer_sessions', ROOT / 'scripts/migrate_admin_sessions.py')
migration = module_from_spec(spec)
spec.loader.exec_module(migration)


@pytest.fixture
def audited(replica):
    db, uid, _, _ = replica
    migration.apply(db)
    now = utcnow()
    actor, target = ObjectId(), uid
    db.users.insert_one({'_id': actor, 'schema_version': 4, 'role': 'admin', 'status': 'active',
                         'is_active': True, 'password_hash': 'local-only'})
    db.users.update_one({'_id': target}, {'$set': {'role': 'customer'}})
    token = 'a' * 64
    auth = 'b' * 64
    db.auth_sessions.insert_one({'_id': token, 'user_id': actor, 'auth_fingerprint': auth,
                                  'expires_at': now + timedelta(hours=1)})
    for _ in range(2):
        db.auth_sessions.insert_one({'user_id': target})
    guard = {'session_id': token, 'auth_fingerprint': auth, 'password_hash': 'local-only',
             'role': 'admin', 'demo_expires_at': None}
    return db, actor, target, AdminSessionService(db, authorization_guard=guard)


def test_real_revocation_receipt_replay_preserves_new_login(audited):
    db, actor, target, service = audited
    operation = str(uuid4())
    assert service.revoke(actor, target, request_id=operation) == 2
    assert db.auth_sessions.count_documents({'user_id': target}) == 0
    new_session = db.auth_sessions.insert_one({'user_id': target}).inserted_id
    assert service.revoke(actor, target, request_id=operation) == 2
    assert db.auth_sessions.find_one({'_id': new_session})
    audit = db.admin_audit_logs.find_one()
    assert audit['actor_id'] == actor and audit['resource_id'] == target
    assert audit['before'] == {'device_count': 2} and audit['after'] == {'device_count': 0}
    assert db.admin_audit_logs.count_documents({}) == db.admin_write_requests.count_documents({}) == 1
    receipt = db.admin_write_requests.find_one()
    assert receipt['expires_at'] - receipt['created_at'] == timedelta(seconds=RETENTION_SECONDS)
    with pytest.raises(CartConflict):
        service.revoke(actor, target, request_id=operation, reason='different operation')
    with pytest.raises(CartConflict):
        service.revoke(actor, ObjectId(), request_id=operation)


def test_real_concurrent_replay_has_one_audit_and_receipt(audited):
    db, actor, target, service = audited
    operation = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: service.revoke(actor, target, request_id=operation), range(2))) == [2, 2]
    assert db.admin_audit_logs.count_documents({}) == db.admin_write_requests.count_documents({}) == 1
    assert db.auth_sessions.count_documents({'user_id': actor}) == 1


@pytest.mark.parametrize('collection', ['admin_audit_logs', 'admin_write_requests'])
def test_real_audit_or_receipt_failure_rolls_back_every_write(audited, monkeypatch, collection):
    db, actor, target, service = audited
    def fail(*args, **kwargs):
        raise OperationFailure('controlled audit write failure')
    from pymongo.synchronous.collection import Collection
    original = Collection.insert_one
    def injected(self, *args, **kwargs):
        if self.name == collection:
            return fail(*args, **kwargs)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Collection, 'insert_one', injected)
    with pytest.raises(OperationFailure):
        service.revoke(actor, target, request_id=str(uuid4()))
    assert db.auth_sessions.count_documents({'user_id': target}) == 2
    assert db.auth_sessions.count_documents({'user_id': actor}) == 1
    assert db.admin_audit_logs.count_documents({}) == db.admin_write_requests.count_documents({}) == 0
    assert 'updated_at' not in db.users.find_one({'_id': target})


@pytest.mark.parametrize('failure', ['role', 'device', 'migration', 'admin_target'])
def test_real_authorization_and_migration_fail_closed(audited, failure):
    db, actor, target, service = audited
    expected = PermissionError
    if failure == 'role':
        db.users.update_one({'_id': actor}, {'$set': {'role': 'customer'}})
    elif failure == 'device':
        db.auth_sessions.delete_many({'user_id': actor})
    elif failure == 'migration':
        db.schema_migrations.delete_one({'_id': MIGRATION})
        expected = PyMongoError
    else:
        db.users.update_one({'_id': target}, {'$set': {'role': 'admin'}})
    with pytest.raises(expected):
        service.revoke(actor, target, request_id=str(uuid4()))
    assert db.auth_sessions.count_documents({'user_id': target}) == 2
    assert db.admin_audit_logs.count_documents({}) == db.admin_write_requests.count_documents({}) == 0


def test_real_receipt_expiry_boundary_rejects_stale_key(audited, monkeypatch):
    from app.services import admin_sessions
    db, actor, target, service = audited
    operation = str(uuid4())
    service.revoke(actor, target, request_id=operation)
    expiry = db.admin_write_requests.find_one()['expires_at'].replace(tzinfo=admin_sessions.timezone.utc)
    monkeypatch.setattr(admin_sessions, 'utcnow', lambda: expiry - timedelta(milliseconds=1))
    assert service.revoke(actor, target, request_id=operation) == 2
    monkeypatch.setattr(admin_sessions, 'utcnow', lambda: expiry)
    with pytest.raises(CartConflict):
        service.revoke(actor, target, request_id=operation)


def test_real_migration_is_read_only_then_repeatable_and_rejects_drift(replica):
    db, _, _, _ = replica
    before = set(db.list_collection_names())
    assert migration.preflight(db)['written'] is False
    assert set(db.list_collection_names()) == before
    migration.apply(db)
    migration.apply(db)
    assert db.schema_migrations.count_documents({'_id': MIGRATION}) == 1
    assert db.admin_audit_logs.options()['validationLevel'] == 'strict'
    db.command('collMod', 'admin_write_requests', validationLevel='moderate')
    with pytest.raises(ValueError, match='validator drift'):
        migration.apply(db)
    assert db.admin_write_requests.options()['validationLevel'] == 'moderate'


@pytest.mark.parametrize('location', ['root', 'before', 'receipt', 'result'])
def test_real_validators_reject_sensitive_extra_fields(audited, location):
    db, actor, target, service = audited
    service.revoke(actor, target, request_id=str(uuid4()))
    collection = db.admin_audit_logs if location in {'root', 'before'} else db.admin_write_requests
    row = collection.find_one()
    row['_id'] = ObjectId()
    row['request_id'] = str(uuid4())
    if location in {'root', 'receipt'}:
        row['password_hash'] = 'forbidden'
    elif location == 'before':
        row['before']['session_token'] = 'forbidden'
    else:
        row['result']['email'] = 'forbidden@example.invalid'
    with pytest.raises(OperationFailure) as error:
        collection.insert_one(row)
    assert error.value.code == 121


def test_migrator_refuses_unreviewed_targets():
    for uri, name in [('mongodb+srv://unused@example.invalid/', 'vibecart_ai'),
                       ('mongodb://user:pass@localhost/', 'ren_acceptance_test'),
                       ('mongodb://localhost/', 'vibecart_ai')]:
        with pytest.raises(ValueError):
            migration.target(uri, name)
