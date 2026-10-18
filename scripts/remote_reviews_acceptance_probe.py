"""Pinned private revision review/ranking acceptance on owned disposable rows.

Credentials arrive on stdin, are never printed, and are restricted by the shared
acceptance host, database and authenticated-role guards. Paid order states and
ranking aggregates here are isolated fixtures, not real payments or public reviews.
"""
import json
import secrets
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from bson import Decimal128, ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from remote_d4_consumer_probe import (
    DATABASE, login, make_event, monitor_count, page, require, verify_database_roles, verify_scope,
)
from remote_member_transaction_checks import csrf_headers, replay_session


def fixture_scope(db, marker, users, products):
    require(db.name == DATABASE and marker.startswith('sam-reviews-'), 'Review cleanup scope mismatch')
    require(users and products and all(isinstance(x, ObjectId) for x in users + products),
            'Review fixture IDs missing')


def cleanup(db, marker, users, products, skus, orders, lines, index):
    fixture_scope(db, marker, users, products)
    result = {}
    if index:
        try:
            db.products.drop_index(index)
            result['temporary_index_removed'] = True
        except Exception:
            result['temporary_index_removed'] = False
    scopes = (
        ('product_reviews', {'$or': [{'product_id': {'$in': products}}, {'order_item_id': {'$in': lines}}]}),
        ('order_items', {'$or': [{'order_id': {'$in': orders}}, {'_id': {'$in': lines}}]}),
        ('orders', {'_id': {'$in': orders}, 'user_id': {'$in': users}}),
        ('behavior_events', {'user_id': {'$in': users}}),
        ('auth_sessions', {'user_id': {'$in': users}}),
        ('users', {'_id': {'$in': users}, 'acceptance_run': marker}),
        ('product_skus', {'_id': {'$in': skus}, 'acceptance_run': marker}),
        ('products', {'_id': {'$in': products}, 'acceptance_run': marker}),
    )
    for name, query in scopes:
        try:
            result[name + '_deleted'] = db[name].delete_many(query).deleted_count
            result[name + '_remaining'] = db[name].count_documents(query)
        except Exception:
            result[name + '_remaining'] = 'readback_failed'
    result['verified'] = all(result.get(name + '_remaining') == 0 for name, _ in scopes)
    result['verified'] = result['verified'] and result.get('temporary_index_removed', True)
    return result


def grids(response):
    require(response.status_code == 200, 'Recommendation HTTP ' + str(response.status_code))
    require(response.headers.get('Cache-Control') == 'private, no-store', 'Recommendation cache policy missing')
    soup = BeautifulSoup(response.text, 'html.parser')
    section = soup.select_one('section[aria-label="猜你喜歡6加4"]')
    require(section is not None, '6+4 section missing')
    groups = section.select('.product-grid')
    require(len(groups) == 2, '6+4 grids missing')
    return [[link['href'].rsplit('/', 1)[-1] for link in group.select('article h3 a')]
            for group in groups]


def run(config):
    verify_scope(config)
    require(type(config.get('expect_bge', True)) is bool, 'Invalid BGE expectation')
    client = MongoClient(config['mongo_uri'], serverSelectionTimeoutMS=15000)
    verify_database_roles(client)
    db = client[DATABASE]
    marker = 'sam-reviews-' + secrets.token_hex(8)
    users, products, skus = [ObjectId() for _ in range(3)], [ObjectId() for _ in range(18)], [ObjectId() for _ in range(18)]
    orders, lines, temporary_index = [], [], None
    report = {'status': 'failed', 'probe_id': marker, 'revision': config['revision'],
              'image': config['image'], 'expect_bge': config.get('expect_bge', True),
              'fixture_scope': 'isolated simulated paid states and ranking aggregates only'}
    base, password = config['service_url'].rstrip('/'), secrets.token_urlsafe(24)
    sessions = []
    try:
        fixture_scope(db, marker, users, products)
        now = datetime.now(timezone.utc)
        major = [ObjectId(), ObjectId()]
        minors = [[ObjectId() for _ in range(3)] for _ in range(2)]
        names = ['評價精確平均測試'] + ['瑜珈伸展偏好商品' + str(i) for i in range(1, 8)]
        names += ['高蛋白跨類商品' + str(i) for i in range(8, 18)]
        docs, sku_docs = [], []
        for i, pid in enumerate(products):
            group = 0 if i < 8 else 1
            stars = 5.0 if i < 8 else [5.0, 4.9, 4.8, 4.7, 4.6, 4.5, 5.0, 4.4, 5.0, 4.8][i - 8]
            docs.append({'_id': pid, 'schema_version': 4, 'product_code': marker + '-' + str(i),
                         'product_name': names[i], 'major_category_id': major[group],
                         'minor_category_id': minors[group][i % 3], 'category_path': ['隔離驗收', '分類' + str(i % 3)],
                         'average_rating_display': stars, 'average_rating_raw': stars,
                         'rating_status': 'ACTUAL', 'rating_count': 10, 'rating_sum': round(stars * 10),
                         'image_urls': [], 'summary': names[i], 'status': 'active',
                         'is_ai_recommendable': True, 'acceptance_run': marker, 'created_at': now})
            sku_docs.append({'_id': skus[i], 'schema_version': 4, 'product_id': pid,
                             'sku_code': marker + '-sku-' + str(i), 'variant_attributes': {},
                             'status': 'active', 'price': Decimal128('10.00'),
                             'available_quantity': 10, 'stock_quantity': 10, 'reserved_quantity': 0,
                             'safety_stock': 0, 'acceptance_run': marker, 'created_at': now})
        docs[0].update(rating_status='DEFAULT', average_rating_display=4.0, average_rating_raw=4.0,
                       rating_default_value=4.0, rating_count=0, rating_sum=0, acceptance_rollback=marker,
                       major_category_id=ObjectId(), minor_category_id=ObjectId())
        docs[16].update(rating_status='DEFAULT', rating_count=0)
        docs[17].update(status='inactive')
        sku_docs[14]['available_quantity'] = 0
        db.products.insert_many(docs)
        db.product_skus.insert_many(sku_docs)
        emails = [marker + '-' + str(i) + '@example.invalid' for i in range(3)]
        db.users.insert_many([{'_id': uid, 'schema_version': 4, 'status': 'active', 'is_active': True,
                              'role': 'admin' if i == 2 else 'customer', 'email': emails[i],
                              'display_name': '隔離評價驗收', 'password_hash': generate_password_hash(password),
                              'acceptance_run': marker, 'created_at': now, 'updated_at': now}
                             for i, uid in enumerate(users)])
        sessions = [csrf_headers(login(base, config['id_token'], email, password), base) for email in emails]
        member, other, admin = sessions

        def line(owner=users[0], **fields):
            order_id, lid = ObjectId(), ObjectId()
            orders.append(order_id)
            lines.append(lid)
            db.orders.insert_one({'_id': order_id, 'schema_version': 4, 'user_id': owner,
                                  'order_number': marker + '-' + str(len(orders)),
                                  'checkout_id': marker + '-' + str(order_id), 'payment_status': 'paid',
                                  'status': 'completed', 'is_demo': True, 'acceptance_run': marker, **fields})
            db.order_items.insert_one({'_id': lid, 'schema_version': 4, 'order_id': order_id,
                                      'user_id': owner, 'product_id': products[0], 'sku_id': skus[0], 'quantity': 1})
            return lid

        def post(lid, rating, session=member, **fields):
            return session.post(base + '/reviews/' + str(lid), json={'rating': rating, **fields},
                                timeout=60, allow_redirects=False)

        report['stage'] = 'eligibility'
        valid = [line() for _ in range(5)]
        invalid = [line(payment_status='unpaid'), line(status='confirmed'),
                   line(status='cancelled', shipping_status='delivered'), line(owner=users[1])]
        for lid in invalid:
            require(post(lid, 5).status_code == 400, 'Ineligible review accepted')
        raw = replay_session(member)
        raw.headers.pop('X-CSRF-Token', None)
        require(post(valid[0], 4, raw).status_code == 400, 'Missing CSRF accepted')
        require(all(post(valid[0], value).status_code == 400 for value in (0, 6, True, '5', 4.5)),
                'Invalid rating accepted')
        require(post(valid[0], 5, other).status_code == 400, 'Other member reviewed owned order')
        require(db.product_reviews.count_documents({'product_id': products[0]}) == 0, 'Rejected review wrote rows')
        report['eligibility'] = {'unpaid_incomplete_cancelled_other_owner_400': True,
                                 'csrf_400': True, 'invalid_rating_400': True}
        report['stage'] = 'default_and_ceiling'
        first = post(valid[0], 4)
        require(first.status_code == 200 and first.json()['rating_count'] == 1 and first.json()['rating'] == 4.0,
                'Default was counted as a review')
        require(post(valid[1], 4).status_code == 200, 'Second review failed')
        before = db.products.find_one({'_id': products[0]})
        # A unique-index conflict happens at the product write, after the review
        # insert inside the same real transaction. Both rows must roll back.
        db.products.update_one({'_id': products[15], 'acceptance_run': marker},
                               {'$set': {'acceptance_rollback': marker, 'average_rating_display': 4.4}})
        temporary_index = marker + '-rollback'
        db.products.create_index([('average_rating_display', 1)], unique=True, name=temporary_index,
                                 partialFilterExpression={'acceptance_rollback': marker})
        failed = post(valid[2], 5)
        require(failed.status_code == 503, 'Controlled product-write conflict not reported')
        require(db.products.find_one({'_id': products[0]}) == before
                and db.product_reviews.count_documents({'product_id': products[0]}) == 2,
                'Review/product transaction did not roll back')
        db.products.drop_index(temporary_index)
        temporary_index = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            replay = list(pool.map(lambda _: post(valid[2], 5, replay_session(member)), range(2)))
        require(all(x.status_code == 200 for x in replay), 'Concurrent identical retry failed')
        require(replay[0].json() == replay[1].json(), 'Identical retry changed receipt')
        product = db.products.find_one({'_id': products[0]})
        require(product['rating_sum'] == 13 and product['rating_count'] == 3
                and product['average_rating_display'] == 4.4, 'Upward rounded 13/3 differs')
        require(post(valid[2], 1).status_code == 409, 'Changed review retry accepted')
        detail = page(member, base + '/product/' + str(products[0]))
        require(detail.select_one('[data-product-rating]').get_text(strip=True) == '★ 4.4'
                and '3筆評價' in detail.get_text(), 'Persisted rating not reflected in HTML')
        require(not detail.select_one('[data-rating-default]'), 'Default marker survived first review')
        report['reviews'] = {'sum': 13, 'count': 3, 'display': 4.4,
                             'concurrent_identical_200': True, 'changed_retry_409': True,
                             'after_insert_product_failure_503_rollback': True,
                             'persisted_html_equal': True, 'default_excluded': True}

        report['stage'] = '6plus4'
        # Seed only owned member behavior, keeping all other users isolated.
        events = [make_event(users[0], products[i], marker, now, False) for i in range(1, 8)]
        db.behavior_events.insert_many(events)
        response = member.get(base + '/recommendations', timeout=190)
        personal, cross = grids(response)
        require(len(personal) == 6 and len(cross) == 4 and len(set(personal + cross)) == 10,
                '6+4 capacity or deduplication differs')
        require(all(ObjectId(x) in products[1:8] for x in personal), 'Own preference candidates missing')
        cross_docs = [db.products.find_one({'_id': ObjectId(x)}) for x in cross]
        ratings = [x['average_rating_display'] for x in cross_docs]
        require(ratings == sorted(ratings, reverse=True) and min(ratings) >= 4.5,
                'Cross-category high-star ordering differs')
        require(all(x['major_category_id'] != major[0] and x['rating_status'] == 'ACTUAL' for x in cross_docs),
                'Default or same-category cross candidate')
        for ids, cap in ((personal, 3), (cross, 2)):
            counts = Counter(db.products.find_one({'_id': ObjectId(x)})['minor_category_id'] for x in ids)
            require(max(counts.values()) <= cap, 'Minor-category cap exceeded')
        require(not any(str(x) in personal + cross for x in (products[14], products[15], products[16], products[17])),
                'Unavailable, low-star, default or inactive candidate leaked')
        other_before = grids(other.get(base + '/recommendations', timeout=190))
        monitor_before = monitor_count(page(admin, base + '/admin/recommendations'))
        db.behavior_events.insert_many([make_event(users[0], products[8], marker, now, True) for _ in range(1001)])
        require(grids(member.get(base + '/recommendations', timeout=190)) == [personal, cross],
                'Synthetic events changed recommendation before limit')
        require(grids(other.get(base + '/recommendations', timeout=190)) == other_before,
                'Another member learned from owned behavior')
        require(monitor_count(page(admin, base + '/admin/recommendations')) == monitor_before,
                'Synthetic history changed attribution monitoring')
        # Insufficient candidates must stay insufficient rather than borrowing
        # default, unavailable or duplicate cards. Only own products are changed.
        db.product_skus.update_many({'_id': {'$in': skus[1:8]}, 'acceptance_run': marker},
                                    {'$set': {'available_quantity': 0}})
        short = grids(member.get(base + '/recommendations', timeout=190))
        require(len(short[0]) <= 6 and len(short[1]) <= 4
                and not any(str(x) in short[0] + short[1] for x in products[1:8]),
                'Insufficient candidates fabricated unavailable cards')
        report['ranking'] = {'personal_count': 6, 'cross_count': 4, 'cross_ratings': ratings,
                             'unique': 10, 'caps_3_and_2': True, 'unavailable_default_excluded': True,
                             'synthetic_1001_unchanged': True, 'other_member_unchanged': True,
                             'synthetic_monitor_count_unchanged': monitor_before,
                             'insufficient_candidates_not_filled_with_unavailable': True}
        report['stage'] = 'different_concurrent_reviews'
        with ThreadPoolExecutor(max_workers=2) as pool:
            parallel = list(pool.map(lambda pair: post(pair[0], pair[1], replay_session(member)),
                                     [(valid[3], 1), (valid[4], 5)]))
        require(all(x.status_code == 200 for x in parallel), 'Concurrent different reviews failed')
        aggregate = db.products.find_one({'_id': products[0]})
        require(aggregate['rating_count'] == 5 and aggregate['rating_sum'] == 19
                and aggregate['average_rating_display'] == 3.8, 'Concurrent aggregate lost a review')
        delivered = line(status='confirmed', shipping_status='delivered')
        form = member.post(base + '/reviews/' + str(delivered), data={
            'csrf_token': member.headers['X-CSRF-Token'], 'rating': '5'},
            timeout=60, allow_redirects=False)
        require(form.status_code == 303 and form.headers.get('Location') == '/product/' + str(products[0]),
                'Delivered order HTML fallback failed')
        report['reviews'].update(concurrent_distinct_reviews_200=True,
                                 concurrent_sum=19, concurrent_count=5, concurrent_display=3.8,
                                 delivered_html_fallback_303=True)
        report['stage'] = 'bge'
        if config.get('expect_bge', True):
            from remote_preview_ai_probe import measured_page, cache_counts
            url = base + '/admin/ai/recommendation?product_id=' + str(products[1])
            first, elapsed = measured_page(admin, url)
            second, cached = measured_page(admin, url)
            one, two = cache_counts(first), cache_counts(second)
            require(two['hits'] == two['total'] and two['total'] > 0, 'BGE vector cache missing')
            report['bge'] = {'real_scores': True, 'first': one, 'second': two,
                             'first_http_ms': elapsed, 'cached_http_ms': cached}
        report['stage'] = 'revoked_device'
        revoked_line = line()
        db.auth_sessions.delete_many({'user_id': users[0]})
        require(post(revoked_line, 5).status_code == 302, 'Revoked session wrote a review')
        require(db.product_reviews.count_documents({'order_item_id': revoked_line}) == 0,
                'Revoked session persisted review')
        report.update(status='passed', revoked_device_denied=True)
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error) if isinstance(error, RuntimeError) else 'Probe failed')
    finally:
        report['fixture_ids'] = {name: [str(x) for x in ids] for name, ids in (
            ('users', users), ('products', products), ('skus', skus), ('orders', orders), ('lines', lines))}
        report['cleanup'] = cleanup(db, marker, users, products, skus, orders, lines, temporary_index)
        if not report['cleanup']['verified']:
            report['status'] = 'cleanup_failed'
        for session in sessions:
            session.close()
        client.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        raise SystemExit(1)
