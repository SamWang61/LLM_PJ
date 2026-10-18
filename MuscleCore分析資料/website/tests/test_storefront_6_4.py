from datetime import datetime, timedelta, timezone
from bson import ObjectId
from app.services.storefront_ranking import recommendations_6_4
from test_v4_routes import shop, post
from test_product_reviews import OfflineReviews, purchased_line


def product(major, minor, rating=4.8, **changes):
    result = dict(_id=ObjectId(), major_category_id=major, minor_category_id=minor, status='active',
        is_ai_recommendable=True, stock=10, rating_status='ACTUAL', rating_count=10,
        average_rating_raw=rating, average_rating_display=rating, name='test')
    return {**result, **changes}


def test_six_plus_four_cross_stars_precede_relation_and_default_is_excluded():
    now = datetime.now(timezone.utc)
    primary, other = ObjectId(), ObjectId()
    personal = [product(primary, ObjectId()) for _ in range(6)]
    cross = [product(other, ObjectId(), stars) for stars in [4.5, 4.7, 4.8, 5.0, 4.9]]
    cross.append(product(other, ObjectId(), 5.0, rating_status='DEFAULT', rating_count=0))
    events = [dict(event_type='PRODUCT_VIEW', product_id=p['_id'], event_at=now) for p in personal]
    rule = dict(antecedent={'major_category_id': primary, 'minor_category_id': personal[0]['minor_category_id']},
        consequent={'major_category_id': other, 'minor_category_id': cross[0]['minor_category_id']},
        status='active', antecedent_customer_count=1000, minimum_sample_size=500,
        co_purchase_count=900, confidence=.9, lift=10)
    result = recommendations_6_4(personal + cross, events, [rule], now=now)
    assert len(result['personalized']) == 6 and len(result['cross_category']) == 4
    assert [r['product']['average_rating_display'] for r in result['cross_category']] == [5.0, 4.9, 4.8, 4.7]
    ids = [str(r['product']['_id']) for key in ('personalized', 'cross_category') for r in result[key]]
    assert len(ids) == len(set(ids)) == 10


def test_caps_stock_recent_purchase_synthetic_and_insufficient_candidates():
    now = datetime.now(timezone.utc)
    major, minor = ObjectId(), ObjectId()
    products = [product(major, minor) for _ in range(8)]
    products += [product(ObjectId(), ObjectId(), stock=0), product(ObjectId(), ObjectId(), status='inactive')]
    result = recommendations_6_4(products, [])
    assert len(result['personalized']) == 3 and len(result['cross_category']) == 2
    assert recommendations_6_4(products, [dict(event_type='PRODUCT_VIEW', event_at=now,
        product_id=products[0]['_id'], metadata={'synthetic': True})]) == result
    durable = product(major, ObjectId(), product_lifecycle_type='durable')
    consumable = product(major, ObjectId(), product_lifecycle_type='consumable', expected_repurchase_interval_days=30)
    events = [dict(event_type='PURCHASE', product_id=p['_id'], event_at=now-timedelta(days=10)) for p in (durable, consumable)]
    result = recommendations_6_4([durable, consumable], events, now=now)
    assert not result['personalized'] and not result['cross_category']
    assert recommendations_6_4([product(major, minor, rating_status='DEFAULT', rating_count=0)], [])['personalized'] == []


def test_review_changes_home_ranking_without_cache_or_batch(shop):
    app, client, db, uid, pid, sid = shop
    app.config['REVIEW_SERVICE_FACTORY'] = OfflineReviews
    lid = purchased_line(db, uid, pid)
    assert '猜你喜歡 · 6＋4' in client.get('/').text
    before = client.get('/recommendations')
    assert '真實高星商品' not in before.text
    assert post(client, f'/reviews/{lid}', rating=5).status_code == 200
    after = client.get('/recommendations')
    assert '★ 5.0' in after.text and '1筆真實評價' in after.text
    assert after.headers['Cache-Control'] == 'private, no-store'
