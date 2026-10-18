"""Review routes and committed aggregates; replica tests also prove rollback/concurrency."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from datetime import timedelta
from threading import Event
import pytest
from bson import ObjectId
from pymongo.errors import ConnectionFailure

from test_v4_routes import shop, post
from test_ren_transactions import replica
from VibeCart_AI.services.review_service import ReviewService
from VibeCart_AI.services.cart_service import CartError


class OfflineReviews(ReviewService):
    def _run(self, callback):
        return callback(None)


def purchased_line(db, uid, pid, **order_fields):
    order = {'_id': ObjectId(), 'user_id': uid, 'payment_status': 'paid', 'status': 'completed', 'checkout_id': str(ObjectId())}
    order.update(order_fields)
    db.orders.insert_one(order)
    line = {'_id': ObjectId(), 'user_id': uid, 'order_id': order['_id'], 'product_id': pid}
    db.order_items.insert_one(line)
    return line['_id']


@pytest.fixture
def reviews(shop):
    app, client, db, uid, pid, sid = shop
    app.config['REVIEW_SERVICE_FACTORY'] = OfflineReviews
    db.product_reviews.create_index([('user_id', 1), ('order_item_id', 1)], unique=True)
    return (*shop, purchased_line(db, uid, pid))


def test_review_updates_default_immediately_replays_and_rejects_changed_payload(reviews):
    _, client, db, uid, pid, _, line = reviews
    page = client.get(f'/product/{pid}')
    assert f'/reviews/{line}' in page.text
    result = post(client, f'/reviews/{line}', rating=3, title='<b>OK</b>', content='hello')
    assert result.status_code == 200
    assert result.json['rating'] == 3.0 and result.json['rating_count'] == 1
    assert result.headers['Cache-Control'] == 'private, no-store'
    assert db.products.find_one({'_id': pid})['rating_sum'] == 3
    assert post(client, f'/reviews/{line}', rating=3, title='<b>OK</b>', content='hello').json == result.json
    assert post(client, f'/reviews/{line}', rating=5).status_code == 409
    page = client.get(f'/product/{pid}')
    assert '★ 3.0' in page.text and '（1筆評價）' in page.text
    assert f'/reviews/{line}' not in page.text
    assert db.product_reviews.count_documents({}) == 1


def test_ceiling_average_counts_reviews_instead_of_displayed_default(reviews):
    _, client, db, uid, pid, _, line = reviews
    for rating, lid in [(4, line), (4, purchased_line(db, uid, pid)), (5, purchased_line(db, uid, pid))]:
        assert post(client, f'/reviews/{lid}', rating=rating).status_code == 200
    product = db.products.find_one({'_id': pid})
    assert product['rating_sum'] == 13 and product['rating_count'] == 3
    assert product['average_rating_display'] == 4.4
    assert product['average_rating_raw'] == pytest.approx(13 / 3)
    assert '★ 4.4' in client.get('/').text


@pytest.mark.parametrize('rating', [0, 6, -1, True, '5', 4.5, None])
def test_invalid_stars_do_not_write(reviews, rating):
    _, client, db, _, _, _, line = reviews
    assert post(client, f'/reviews/{line}', rating=rating).status_code == 400
    assert db.product_reviews.count_documents({}) == 0


@pytest.mark.parametrize('fields', [dict(payment_status='unpaid'), dict(status='confirmed'),
                                  dict(status='cancelled', shipping_status='delivered')])
def test_unpaid_undelivered_cancelled_are_not_reviewable(reviews, fields):
    _, client, db, uid, pid, _, _ = reviews
    line = purchased_line(db, uid, pid, **fields)
    assert post(client, f'/reviews/{line}', rating=5).status_code == 400
    assert f'/reviews/{line}' not in client.get(f'/product/{pid}').text


def test_owner_csrf_readonly_and_database_errors(reviews, monkeypatch):
    app, client, db, uid, pid, _, line = reviews
    other_line = purchased_line(db, ObjectId(), pid)
    assert post(client, f'/reviews/{other_line}', rating=5, user_id=str(uid)).status_code == 400
    assert client.post(f'/reviews/{line}', json={'rating': 5}).status_code == 400
    app.config['CLOUD_PREVIEW_READ_ONLY'] = True
    assert post(client, f'/reviews/{line}', rating=5).status_code == 403
    app.config['CLOUD_PREVIEW_READ_ONLY'] = False
    def unavailable(*args, **kwargs):
        raise ConnectionFailure('private-database-host')
    monkeypatch.setattr(OfflineReviews, 'create_review', unavailable)
    response = post(client, f'/reviews/{line}', rating=5)
    assert response.status_code == 503 and 'private-database-host' not in response.text


def test_html_fallback_delivered_and_revoked_device(reviews):
    _, client, db, uid, pid, _, _ = reviews
    line = purchased_line(db, uid, pid, status='confirmed', shipping_status='delivered')
    response = client.post(f'/reviews/{line}', data={'csrf_token': 'test-csrf', 'rating': '5'})
    assert response.status_code == 303 and response.location == f'/product/{pid}'
    db.auth_sessions.delete_many({'user_id': uid})
    assert post(client, f'/reviews/{line}', rating=5).status_code == 302


def test_real_review_rollback_and_hidden_reviews_excluded(replica):
    db, uid, pid, _ = replica
    line = purchased_line(db, uid, pid)
    before = deepcopy(db.products.find_one({'_id': pid}))
    class Failing(ReviewService):
        def _authorize_commit(self, *args):
            raise CartError('revoked after product write')
    with pytest.raises(CartError):
        Failing(db).create_review(uid, line, 5)
    assert db.products.find_one({'_id': pid}) == before
    assert db.product_reviews.count_documents({}) == 0
    db.product_reviews.insert_one({'product_id': pid, 'user_id': ObjectId(), 'order_item_id': ObjectId(),
                                   'rating': 1, 'status': 'hidden'})
    ReviewService(db).create_review(uid, line, 5)
    assert db.products.find_one({'_id': pid})['average_rating_display'] == 5.0


def test_real_concurrent_reviews_and_identical_replay(replica):
    db, uid, pid, _ = replica
    db.product_reviews.create_index([('user_id', 1), ('order_item_id', 1)], unique=True)
    lines = [purchased_line(db, uid, pid) for _ in range(3)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda pair: ReviewService(db).create_review(uid, *pair), zip(lines, [4, 4, 5])))
    product = db.products.find_one({'_id': pid})
    assert product['rating_count'] == 3 and product['rating_sum'] == 13
    assert product['average_rating_display'] == 4.4
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ReviewService(db).create_review(uid, lines[0], 4), range(2)))
    assert results[0]['_id'] == results[1]['_id']
    assert db.product_reviews.count_documents({}) == 3


def test_real_device_revoked_after_review_writes_rolls_back(replica):
    db, uid, pid, _ = replica
    db.users.update_one({'_id': uid}, {'$set': {'role': 'customer', 'password_hash': 'before'}})
    now = datetime.now(timezone.utc)
    auth = dict(_id='f'*64, user_id=uid, auth_fingerprint='e'*64, expires_at=now+timedelta(hours=1))
    db.auth_sessions.insert_one(auth)
    guard = dict(session_id=auth['_id'], auth_fingerprint=auth['auth_fingerprint'],
                 role='customer', password_hash='before', demo_expires_at=None)
    line = purchased_line(db, uid, pid)
    before = deepcopy(db.products.find_one({'_id': pid}))
    reached, release = Event(), Event()
    class Paused(ReviewService):
        def _authorize_commit(self, *args):
            if not reached.is_set():
                reached.set()
                assert release.wait(10)
            return super()._authorize_commit(*args)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(Paused(db, authorization_guard=guard).create_review, uid, line, 5)
        try:
            assert reached.wait(10)
            assert db.auth_sessions.delete_one({'_id': auth['_id']}).deleted_count == 1
        finally:
            release.set()
        with pytest.raises(CartError):
            future.result(timeout=20)
    assert db.product_reviews.count_documents({}) == 0
    assert db.products.find_one({'_id': pid}) == before
