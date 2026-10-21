from copy import deepcopy
from html import unescape
import re
from bson import ObjectId
from test_v4_routes import shop


def test_detail_uses_bounded_same_category_reads_and_preserves_return_context(shop, monkeypatch):
    from app import store_v4
    _, client, db, _, pid, sid = shop
    def forbidden(*_): raise AssertionError('Detail must not load the full catalog')
    monkeypatch.setattr(store_v4, 'catalog', forbidden)
    template = db.products.find_one({'_id': pid})
    sku = db.product_skus.find_one({'_id': sid})
    related = []
    for i in range(8):
        p = deepcopy(template); p.update(_id=ObjectId(), product_name=f'Same category {i}')
        db.products.insert_one(p)
        s = deepcopy(sku); s.update(_id=ObjectId(), product_id=p['_id'])
        db.product_skus.insert_one(s); related.append(p['_id'])
    db.products.update_one({'_id': related[0]}, {'$set': {'status': 'inactive'}})
    db.products.update_one({'_id': related[1]}, {'$set': {'minor_category_id': ObjectId()}})
    response = client.get(f'/product/{pid}?page=2&major=sport&category=weight&q=Browse')
    assert response.status_code == 200
    text = unescape(response.text)
    assert 'page=2' in text and 'q=Browse' in text and 'major=sport' in text and 'category=weight' in text
    assert 'rel="prev"' not in text and 'rel="next"' not in text
    links = re.findall(r'class="card-link" href="/product/([a-f0-9]{24})', text)
    assert links == [str(i) for i in related[2:6]]


def test_stock_and_price_are_fresh_and_sold_out_controls_are_disabled(shop):
    _, client, db, _, pid, sid = shop
    initial = client.get(f'/product/{pid}')
    assert 'TEST-1' not in initial.text and '5kg' in initial.text
    db.product_skus.update_one({'_id': sid}, {'$set': {'available_quantity': 0}})
    response = client.get(f'/product/{pid}')
    assert '已售完，補貨中' in response.text
    assert re.search(r'name="quantity"[^>]+disabled', response.text)
    assert re.search(r'type="submit"\s+disabled', response.text)
    assert response.headers['Cache-Control'] == 'private, no-store'


def test_empty_recommendations_keep_refresh_target_without_blank_sections(shop):
    _, client, _, _, _, _ = shop
    with client.session_transaction() as state: state.clear()
    response = client.get('/')
    assert response.status_code == 200
    assert 'id="recommendation-blocks"' in response.text
    assert 'aria-label="猜你喜歡6加4"' not in response.text
    assert '暫無推薦' not in response.text
    assert 'class="card-link"' in response.text


def test_expired_csrf_has_recovery_links_and_stays_rejected(shop):
    _, client, _, _, _, _ = shop
    response = client.post('/auth/logout', data={'csrf_token': 'wrong'})
    assert response.status_code == 400
    assert '表單已失效' in response.text and '回首頁' in response.text and '重新登入' in response.text
    with client.session_transaction() as state: assert state.get('user_id')
