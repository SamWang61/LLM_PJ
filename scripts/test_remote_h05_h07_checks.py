"""A green remote report must reject incomplete/linkless/replayed event evidence."""
from datetime import datetime, timezone
from unittest.mock import MagicMock
import mongomock
import pytest
from bson import ObjectId
from remote_h05_h07_checks import cart_checks, event_checks
from remote_d4_consumer_probe import page
import requests


@pytest.fixture
def evidence():
    db = mongomock.MongoClient().vibecart_acceptance_pr21
    uid, pid, cart, order = (ObjectId() for _ in range(4))
    for kind in ('SEARCH', 'PRODUCT_VIEW', 'ADD_TO_CART', 'PURCHASE'):
        db.behavior_events.insert_one({
            'schema_version': 4, 'event_id': kind, 'session_id': 'fixture-session',
            'user_id': uid, 'event_type': kind, 'event_at': datetime.now(timezone.utc),
            'product_id': None if kind == 'SEARCH' else pid,
            'search_query': 'marker' if kind == 'SEARCH' else None,
            'order_id': order if kind == 'PURCHASE' else None, 'cart_id': cart,
            'metadata': {'exclude_from_attribution': True} if kind == 'PURCHASE' else {}})
    return db, uid, pid, cart, order, 'marker'


def test_complete_evidence_is_scoped_to_its_user(evidence):
    db, *_ = evidence
    db.behavior_events.insert_one({'user_id': ObjectId(), 'event_type': 'PURCHASE'})
    assert event_checks(*evidence)['event_type_counts'] == {
        'SEARCH': 1, 'PRODUCT_VIEW': 1, 'ADD_TO_CART': 1, 'PURCHASE': 1}


@pytest.mark.parametrize('update', [
    {'$unset': {'session_id': ''}},
    {'$set': {'order_id': ObjectId()}},
    {'$set': {'cart_id': ObjectId()}},
    {'$set': {'metadata': {}}},
    {'$set': {'event_id': 'SEARCH'}},
])
def test_incomplete_or_misattributed_purchase_never_passes(evidence, update):
    evidence[0].behavior_events.update_one({'event_type': 'PURCHASE'}, update)
    with pytest.raises(RuntimeError):
        event_checks(*evidence)


def test_missing_event_type_fails(evidence):
    evidence[0].behavior_events.delete_one({'event_type': 'PRODUCT_VIEW'})
    with pytest.raises(RuntimeError, match='four event types'):
        event_checks(*evidence)


def test_h05_refuses_production_or_foreign_fixture_before_http():
    db, session = MagicMock(), MagicMock()
    ids = [ObjectId() for _ in range(3)]
    db.name = 'vibecart_ai'
    with pytest.raises(RuntimeError, match='scope mismatch'):
        cart_checks(db, session, 'https://unused.invalid', 'marker', *ids)
    db.name = 'vibecart_acceptance_pr21'
    db.__getitem__.return_value.count_documents.return_value = 0
    with pytest.raises(RuntimeError, match='ownership mismatch'):
        cart_checks(db, session, 'https://unused.invalid', 'marker', *ids)
    session.get.assert_not_called()
    session.post.assert_not_called()


def test_get_transport_retry_preserves_cookies_and_never_posts(monkeypatch):
    monkeypatch.setattr('remote_d4_consumer_probe.time.sleep', lambda _: None)
    session = MagicMock()
    response = MagicMock(status_code=200, text='<h1>recovered</h1>')
    session.get.side_effect = [requests.ReadTimeout(), response]
    assert page(session, 'https://unused.invalid/product/fixture').h1.text == 'recovered'
    session.close.assert_called_once()
    session.post.assert_not_called()


def test_exhausted_transport_does_not_disclose_url_query_or_exception(monkeypatch):
    monkeypatch.setattr('remote_d4_consumer_probe.time.sleep', lambda _: None)
    session = MagicMock()
    session.get.side_effect = requests.ReadTimeout('private-credential-value')
    with pytest.raises(RuntimeError) as error:
        page(session, 'https://unused.invalid/cart?private=value')
    assert str(error.value) == 'GET /cart transport failed after 3 attempts (ReadTimeout)'
    assert session.get.call_count == 3
    session.post.assert_not_called()
