"""Read back v4 schemas; optional real Flask/transaction smoke test with owned fixtures.

No URI, passwords or provider exception text is emitted. No historical migrations run.
"""
import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4
from decimal import Decimal
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'VibeCart_AI/MongoDB'))
sys.path.insert(0, str(ROOT / 'MuscleCore分析資料/website'))


def smoke(db):
    from bson import Decimal128
    from flask import g
    from app import create_app
    from test_complete_v4 import example
    from app.services.sku_gateway import CartService, CartError
    from concurrent.futures import ThreadPoolExecutor
    from werkzeug.security import generate_password_hash
    marker = 'sam-uat-' + uuid4().hex
    password = uuid4().hex
    email = marker + '@example.test'
    owned = {name: [] for name in ('users', 'products', 'product_skus', 'categories')}
    checks = []
    def insert(name, **updates):
        document = example(name)
        document.update(updates)
        owned[name].append(document['_id'])
        db[name].insert_one(document)
        return document
    app = create_app({'TESTING': True, 'SECRET_KEY': uuid4().hex, 'DATA_MODE': 'v4',
                      'ENABLE_CHECKOUT': True, 'AI_RECOMMENDATIONS_ENABLED': False, 'AI_SUMMARY_ENABLED': False})
    @app.before_request
    def inject():
        g.db = db
    client = app.test_client()
    def post(path, **payload):
        return client.post(path, json=payload, headers={'X-CSRF-Token': 'uat-csrf'})
    try:
        with client.session_transaction() as session:
            session['csrf_token'] = 'uat-csrf'
        response = client.post('/auth/register', data={'csrf_token': 'uat-csrf', 'email': email, 'password': password, 'name': 'SAM 測試會員'})
        user = db.users.find_one({'email': email})
        assert response.status_code == 302 and user and user['schema_version'] == 4
        owned['users'].append(user['_id'])
        # Registration rotates the session; obtain a fresh form token before login.
        client.get('/auth/login')
        with client.session_transaction() as session:
            login_csrf = session['csrf_token']
        response = client.post('/auth/login', data={'csrf_token': login_csrf, 'email': email, 'password': password})
        assert response.status_code == 302
        with client.session_transaction() as session:
            assert session['user_id'] == str(user['_id'])
            session['csrf_token'] = 'uat-csrf'
        checks.append('v4_register_login_with_strict_validator')
        major = insert('categories')
        minor = insert('categories', level=2, category_code=marker, parent_id=major['_id'], path=[major['category_code'], marker])
        product = insert('products', major_category_id=major['_id'], minor_category_id=minor['_id'], category_path=minor['path'], product_name=marker)
        sku = insert('product_skus', product_id=product['_id'], price=Decimal128('12.25'), stock_quantity=3, reserved_quantity=0, available_quantity=3, stock_status='in_stock')
        assert client.get('/').status_code == 200
        assert client.get('/product/' + str(product['_id'])).status_code == 200
        assert post('/cart/add/' + str(product['_id']), sku_id=str(sku['_id']), quantity=2, operation_id=marker).status_code == 200
        assert post('/cart/update/' + str(sku['_id']), quantity=1, operation_id=marker+'-update').status_code == 200
        assert post('/cart/remove/' + str(sku['_id']), operation_id=marker+'-remove').status_code == 200
        assert post('/cart/add/' + str(product['_id']), sku_id=str(sku['_id']), quantity=2, operation_id=marker+'-readd').status_code == 200
        cart = db.carts.find_one({'user_id': user['_id'], 'status': 'active'})
        payload = {'cart_id': str(cart['_id']), 'expected_revision': cart['revision'], 'checkout_id': marker+'-checkout'}
        assert post('/checkout', **payload).status_code == 200
        assert post('/checkout', **payload).status_code == 200
        assert db.orders.count_documents({'user_id': user['_id']}) == 1
        assert db.orders.find_one({'user_id': user['_id']})['total_amount'].to_decimal() == Decimal('24.50')
        assert db.product_skus.find_one({'_id': sku['_id']})['available_quantity'] == 1
        checks.append('flask_cart_mutations_and_idempotent_transaction_checkout')
        assert client.get('/admin/').status_code == 302
        db.users.update_one({'_id': user['_id']}, {'$set': {'role': 'admin'}})
        assert client.get('/admin/').status_code == 200
        assert client.get('/admin/recommendations').status_code == 200
        assert post('/admin/summary').status_code == 200
        db.users.update_one({'_id': user['_id']}, {'$set': {'role': 'customer'}})
        assert client.get('/admin/').status_code == 302
        checks.append('live_admin_metrics_monitor_summary_and_revocation')
        # Two separately owned members compete for the final unit.
        buyers = [insert('users', password_hash=generate_password_hash(uuid4().hex)) for _ in range(2)]
        service = CartService(db, enable_checkout=True)
        # Verify that an actual write is rolled back on an application exception.
        rollback_user = example('users')
        owned['users'].append(rollback_user['_id'])
        def rollback_probe(session):
            db.users.insert_one(rollback_user, session=session)
            raise RuntimeError('deliberate-rollback')
        try:
            service._run(rollback_probe)
        except RuntimeError:
            pass
        assert db.users.count_documents({'_id': rollback_user['_id']}) == 0
        checks.append('real_transaction_write_rollback')
        for i, buyer in enumerate(buyers):
            service.add_item(buyer['_id'], sku['_id'], 1, operation_id=marker+'-race-add-'+str(i))
        def purchase(pair):
            i, buyer = pair
            active = db.carts.find_one({'user_id': buyer['_id'], 'status': 'active'})
            try:
                service.checkout_cart(buyer['_id'], cart_id=active['_id'], expected_revision=active['revision'], checkout_id=marker+'-race-'+str(i))
                return 'paid'
            except CartError:
                return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(purchase, enumerate(buyers)))
        assert sorted(results) == ['paid', 'rejected']
        assert db.product_skus.find_one({'_id': sku['_id']})['available_quantity'] == 0
        checks.append('real_transaction_last_stock_concurrency')
        return checks
    finally:
        # Only this invocation's generated IDs/email are eligible for cleanup.
        created = db.users.find_one({'email': email}, {'_id': 1})
        if created and created['_id'] not in owned['users']:
            owned['users'].append(created['_id'])
        for name in ('product_reviews', 'order_items', 'orders', 'carts', 'cart_events', 'behavior_events'):
            db[name].delete_many({'user_id': {'$in': owned['users']}})
        for name, ids in owned.items():
            db[name].delete_many({'_id': {'$in': ids}})


def main():
    from dotenv import dotenv_values
    from pymongo import MongoClient
    from schema_complete_v4 import verify_complete, SCHEMAS
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--smoke', action='store_true', help='Write and remove uniquely owned test fixtures')
    parser.add_argument('--report')
    args = parser.parse_args()
    config = dotenv_values(args.env_file)
    if (urlparse(config.get('MONGO_URI', '')).hostname != 'vibecart-ai-free.odqe25w.mongodb.net'
            or config.get('MONGO_DB') != 'vibecart_ai' or config.get('DATA_MODE') != 'v4'):
        raise ValueError('Unexpected test target; review configuration')
    with MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=10000, tz_aware=True) as client:
        db = client[config['MONGO_DB']]
        rows = verify_complete(db)
        before = {n: db[n].count_documents({}) for n in SCHEMAS}
        checks = smoke(db) if args.smoke else []
        after = {n: db[n].count_documents({}) for n in SCHEMAS}
        assert before == after, 'Collection counts changed; inspect owned fixture cleanup'
        verified = verify_complete(db)
        from datetime import datetime, timezone
        report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'database': config['MONGO_DB'],
                  'isolated_new_database': False, 'collections': [{'name': r['collection'], 'count': r['count'],
                  'conforming': r['conforming_documents'], 'indexes': len(r['indexes'])} for r in verified],
                  'total_indexes': sum(len(r['indexes']) for r in rows), 'smoke_checks': checks,
                  'fixture_counts_restored': before == after,
                  'migrations': [{'id': x['_id'], 'status': x['status']} for x in db.schema_migrations.find({})]}
        if args.report:
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import traceback
        frames = [{'file': Path(f.filename).name, 'line': f.lineno} for f in traceback.extract_tb(error.__traceback__)]
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__, 'code': getattr(error, 'code', None), 'frames': frames}))
        raise SystemExit(1)
