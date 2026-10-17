"""Deep checks must reject a production target or foreign fixtures before mutations."""
from unittest.mock import MagicMock
import pytest
import requests
import mongomock
from bson import ObjectId
import remote_member_transaction_checks as probe
from remote_transaction_acceptance_probe import cleanup_transaction_probe


def test_replay_copies_cookie_and_headers_without_mutating_original():
    original=requests.Session()
    original.headers['Authorization']='Bearer unused-test-token'
    original.cookies.set('__session','old-test-cookie')
    replay=probe.replay_session(original)
    original.cookies.set('__session','new-test-cookie')
    assert replay.cookies.get('__session')=='old-test-cookie'
    assert replay.headers['Authorization']=='Bearer unused-test-token'
    assert original.cookies.get('__session')=='new-test-cookie'


def test_wrong_database_is_rejected_before_collection_access():
    db=MagicMock();db.name='vibecart_ai'
    with pytest.raises(RuntimeError,match='database mismatch'):
        probe.scope(db,'marker',[ObjectId()],[ObjectId()],ObjectId())
    db.__getitem__.assert_not_called()


def test_foreign_fixture_is_rejected_before_insert_or_update():
    db=MagicMock();db.name='vibecart_acceptance_pr21'
    db.__getitem__.return_value.count_documents.return_value=0
    with pytest.raises(RuntimeError,match='fixture ownership'):
        probe.scope(db,'marker',[ObjectId()],[ObjectId()],ObjectId())
    db.users.insert_one.assert_not_called()
    db.users.update_one.assert_not_called()


def test_production_config_is_rejected_before_fixture_or_connection_use():
    db=MagicMock()
    config={'mongo_uri':'mongodb+srv://unused@vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai'}
    with pytest.raises(RuntimeError,match='scope mismatch'):
        probe.run(db,config,'marker',None,None,None,'unused','unused',[],[],{})
    db.__getitem__.assert_not_called()


def test_rollback_readback_detects_items_without_user_or_parent_and_cart_events():
    db = mongomock.MongoClient()['vibecart_acceptance_pr21']
    user_id, sku_id, cart_id, order_id = (ObjectId() for _ in range(4))
    db.carts.insert_one({'_id':cart_id, 'user_id':user_id})
    db.orders.insert_one({'_id':order_id, 'user_id':user_id})
    db.order_items.insert_one({'order_id':order_id, 'sku_id':sku_id})
    db.cart_events.insert_one({'cart_id':cart_id})
    before = probe.persisted_counts(db, [user_id], [sku_id])
    assert before['order_items'] == 1 and before['cart_events'] == 1
    # Exercise anomalous partial rows, not the normal checkout line (which
    # includes user_id). User-only queries do not see these extra rows.
    db.order_items.insert_one({'order_id':ObjectId(), 'sku_id':sku_id})
    db.cart_events.insert_one({'cart_id':cart_id})
    db.order_items.insert_one({'order_id':ObjectId(), 'sku_id':ObjectId()})
    db.cart_events.insert_one({'cart_id':ObjectId()})
    after = probe.persisted_counts(db, [user_id], [sku_id])
    assert after['order_items'] == 2 and after['cart_events'] == 2
    assert before != after and after['orders'] == before['orders'] == 1


def test_cleanup_deletes_orphan_items_by_fixture_sku_and_preserves_foreign_rows():
    db = mongomock.MongoClient()['vibecart_acceptance_pr21']
    uid, sku, pid, order, cart, foreign_sku = (ObjectId() for _ in range(6))
    marker = 'ren-txn-cleanup-regression'
    db.users.insert_one({'_id':uid, 'acceptance_run':marker})
    db.products.insert_one({'_id':pid, 'acceptance_run':marker})
    db.product_skus.insert_one({'_id':sku, 'acceptance_run':marker})
    db.orders.insert_one({'_id':order, 'user_id':uid})
    db.carts.insert_one({'_id':cart, 'user_id':uid})
    db.cart_events.insert_one({'cart_id':cart})
    db.order_items.insert_many([
        {'order_id':order, 'sku_id':sku},
        {'order_id':ObjectId(), 'sku_id':sku},  # Parent absent; must still be deleted.
        {'order_id':ObjectId(), 'sku_id':foreign_sku},
    ])
    result = cleanup_transaction_probe(db, marker, [uid], [sku], pid)
    assert result['verified'] is True and result['order_items'] == 2
    assert result['order_items_remaining'] == 0
    assert db.order_items.count_documents({}) == 1
    assert db.order_items.find_one()['sku_id'] == foreign_sku


def test_cleanup_refuses_production_database_before_access():
    db = MagicMock(); db.name = 'vibecart_ai'
    with pytest.raises(RuntimeError, match='database scope'):
        cleanup_transaction_probe(db, 'ren-txn-unused', [ObjectId()], [ObjectId()], ObjectId())
    db.orders.find.assert_not_called()


def test_cleanup_leftover_or_unreadable_items_cannot_be_verified(monkeypatch):
    db = mongomock.MongoClient()['vibecart_acceptance_pr21']
    uid, sku, pid = (ObjectId() for _ in range(3))
    monkeypatch.setattr(db.order_items, 'count_documents', lambda _: 1)
    result = cleanup_transaction_probe(db, 'ren-txn-leftover', [uid], [sku], pid)
    assert result['verified'] is False and result['order_items_remaining'] == 1
    def unreadable(_):
        raise RuntimeError('simulated readback failure')
    monkeypatch.setattr(db.order_items, 'count_documents', unreadable)
    result = cleanup_transaction_probe(db, 'ren-txn-leftover', [uid], [sku], pid)
    assert result['verified'] is False and result['order_items_remaining'] == 'readback_failed'
