"""Actual MongoDB transactions, synchronized after order/item writes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest
from app.services.sku_gateway import CartService, CartError
from app.services.member_sessions import demo_expiration, account_unexpired
from test_ren_transactions import replica
from test_v4_routes import shop


@pytest.mark.parametrize('change', ['session', 'disable', 'password', 'role'])
def test_revocation_during_checkout_rolls_back_every_business_write(replica, change):
    db, uid, _, sid = replica
    db.users.update_one({'_id': uid}, {'$set': {'role': 'customer', 'password_hash': 'before'}})
    now = datetime.now(timezone.utc)
    session_doc = {'_id': 'a' * 64, 'schema_version': 4, 'user_id': uid,
                   'auth_fingerprint': 'b' * 64, 'created_at': now,
                   'expires_at': now + timedelta(days=1)}
    db.auth_sessions.insert_one(session_doc)
    guard = {'session_id': session_doc['_id'], 'auth_fingerprint': session_doc['auth_fingerprint'],
             'role': 'customer', 'password_hash': 'before', 'demo_expires_at': None}
    cart = CartService(db, enable_checkout=True, authorization_guard=guard).add_item(
        uid, sid, 1, operation_id='add')
    reached, release = Event(), Event()

    class Paused(CartService):
        def _behavior(self, *args, **kwargs):
            if args[3] == 'PURCHASE' and not reached.is_set():
                reached.set()
                assert release.wait(10)
            return super()._behavior(*args, **kwargs)

    def checkout():
        with pytest.raises(CartError):
            Paused(db, enable_checkout=True, authorization_guard=guard).checkout_cart(
                uid, checkout_id='revoked', cart_id=cart['_id'], expected_revision=cart['revision'])

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(checkout)
        try:
            assert reached.wait(10), 'Must reach the point after real order/item writes'
            if change == 'session':
                assert db.auth_sessions.delete_one({'_id': session_doc['_id']}).deleted_count == 1
            else:
                fields = {'disable': {'is_active': False, 'status': 'inactive'},
                          'password': {'password_hash': 'changed'}, 'role': {'role': 'admin'}}[change]
                db.users.update_one({'_id': uid}, {'$set': fields})
        finally:
            release.set()
        future.result(timeout=20)
    assert db.orders.count_documents({}) == db.order_items.count_documents({}) == 0
    assert db.behavior_events.count_documents({'event_type': 'PURCHASE'}) == 0
    assert db.cart_events.count_documents({'event_type': 'CHECKOUT'}) == 0
    assert db.product_skus.find_one({'_id': sid})['available_quantity'] == 2
    assert db.carts.find_one({'_id': cart['_id']})['revision'] == cart['revision']
    assert db.carts.find_one({'_id': cart['_id']})['status'] == 'active'
    if change == 'session':
        assert db.auth_sessions.count_documents({'_id': session_doc['_id']}) == 0


def test_reserved_demo_identity_expiry_and_normal_members(monkeypatch):
    cutoff = datetime(2026, 10, 18, 12, 30, tzinfo=timezone.utc)
    from app.services import member_sessions as m
    demo = {'email': 'ren-20261018T123000Z@demo.vibecart.invalid'}
    assert demo_expiration(demo) == cutoff
    monkeypatch.setattr(m, 'utcnow', lambda: cutoff - timedelta(seconds=1))
    assert account_unexpired(demo)
    monkeypatch.setattr(m, 'utcnow', lambda: cutoff)
    assert not account_unexpired(demo)
    assert not account_unexpired({'email': 'malformed@demo.vibecart.invalid'})
    assert account_unexpired({'email': 'normal@example.invalid'})


def test_expired_demo_rejects_existing_cookie_and_new_login(shop):
    _, browser, db, uid, _, _ = shop
    email = 'ren-20000101t000000z@demo.vibecart.invalid'
    db.users.update_one({'_id': uid}, {'$set': {'email': email}})
    assert browser.get('/cart').status_code == 302
    with browser.session_transaction() as state:
        state['csrf_token'] = 'expiry-test'
    result = browser.post('/auth/login', data={'email': email, 'password': 'test-password',
                                              'csrf_token': 'expiry-test'})
    assert result.status_code == 200
    assert browser.get('/cart').status_code == 302


def test_session_lease_preserves_expiry_fingerprint_and_creation(replica):
    db, uid, _, sid = replica
    now = datetime.now(timezone.utc)
    db.users.update_one({'_id': uid}, {'$set': {'role': 'customer', 'password_hash': 'before'}})
    db.auth_sessions.insert_one({'_id': 'c' * 64, 'schema_version': 4, 'user_id': uid,
        'auth_fingerprint': 'd' * 64, 'created_at': now, 'expires_at': now + timedelta(days=1)})
    original = db.auth_sessions.find_one({'_id': 'c' * 64})
    guard = {'session_id': original['_id'], 'auth_fingerprint': original['auth_fingerprint'],
             'role': 'customer', 'password_hash': 'before', 'demo_expires_at': None}
    service = CartService(db, enable_checkout=True, authorization_guard=guard)
    cart = service.add_item(uid, sid, 1, operation_id='add-lease')
    order = service.checkout_cart(uid, cart_id=cart['_id'], expected_revision=cart['revision'],
                                  checkout_id='checkout-lease')
    assert order['status'] == 'confirmed'
    assert db.auth_sessions.find_one({'_id': original['_id']}) == original
