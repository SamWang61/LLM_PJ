"""Isolated HTTP/Atlas checkout fault and mid-transaction revocation probe."""
import json
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from bson import ObjectId, Decimal128
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash
from remote_d4_consumer_probe import verify_scope, verify_database_roles, require, login, page
from remote_transaction_acceptance_probe import cleanup_transaction_probe


def run(config):
    verify_scope(config)
    client = MongoClient(config['mongo_uri'], serverSelectionTimeoutMS=15000)
    db = client['vibecart_acceptance_pr21']
    verify_database_roles(client)
    marker = 'ren-txn-fault-' + secrets.token_hex(8)
    report = {'probe_id': marker, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'status': 'failed', 'baseline_reproduction': bool(config.get('baseline')),
              'acceptance_passed': False, 'cases': {}}
    users, skus, indexes = [], [], []
    pid = ObjectId()
    base = config['service_url'].rstrip('/')
    try:
        template = db.products.find_one({'schema_version': 4, 'status': 'active'})
        require(template, 'Acceptance catalog missing')
        now = datetime.now(timezone.utc)
        db.products.insert_one({'_id': pid, 'schema_version': 4, 'product_code': marker,
            'product_name': '隔離故障驗收商品', 'major_category_id': template['major_category_id'],
            'minor_category_id': template['minor_category_id'], 'category_path': template['category_path'],
            'status': 'active', 'average_rating_display': 0, 'image_urls': [],
            'summary': 'Disposable private fault probe', 'is_ai_recommendable': False,
            'acceptance_run': marker, 'created_at': now})

        def fixture(label):
            uid, sid = ObjectId(), ObjectId()
            users.append(uid); skus.append(sid)
            email, password = marker + '-' + label + '@example.invalid', secrets.token_urlsafe(24)
            db.users.insert_one({'_id': uid, 'schema_version': 4, 'status': 'active',
                'is_active': True, 'role': 'customer', 'email': email,
                'display_name': '隔離 ' + label, 'password_hash': generate_password_hash(password),
                'created_at': now, 'updated_at': now, 'acceptance_run': marker})
            db.product_skus.insert_one({'_id': sid, 'schema_version': 4, 'product_id': pid,
                'sku_code': marker + '-' + label, 'variant_attributes': {}, 'status': 'active',
                'price': Decimal128('10.00'), 'available_quantity': 4, 'stock_quantity': 4,
                'reserved_quantity': 0, 'safety_stock': 0, 'created_at': now, 'acceptance_run': marker})
            browser = login(base, config['id_token'], email, password)
            field = page(browser, base + '/').select_one('form[action="/auth/logout"] input[name="csrf_token"]')
            browser.headers['X-CSRF-Token'] = field['value']
            return uid, sid, browser

        def add(uid, sid, browser, label):
            r = browser.post(base + '/cart/add/' + str(pid), json={'sku_id': str(sid),
                'quantity': 1, 'operation_id': marker + '-add-' + label}, timeout=40)
            require(r.status_code == 200, 'Fixture cart add failed')
            cart = db.carts.find_one({'user_id': uid, 'status': 'active'})
            return {'cart_id': str(cart['_id']), 'expected_revision': cart['revision'],
                    'checkout_id': marker + '-checkout-' + label}

        def snapshot(uid, sid):
            cart = db.carts.find_one({'user_id': uid, 'status': 'active'})
            sku = db.product_skus.find_one({'_id': sid})
            return {'available': sku['available_quantity'], 'stock': sku['stock_quantity'],
                'cart_revision': cart['revision'] if cart else None,
                'cart_status': cart['status'] if cart else None,
                'orders': db.orders.count_documents({'user_id': uid}),
                'items': db.order_items.count_documents({'user_id': uid}),
                'behavior': db.behavior_events.count_documents({'user_id': uid}),
                'cart_events': db.cart_events.count_documents({'user_id': uid})}

        if not config.get('baseline'):
            # A real server DuplicateKeyError after the SKU mutation, not a shortage.
            uid, sid, browser = fixture('unique')
            payload = add(uid, sid, browser, 'unique-initial')
            require(browser.post(base + '/checkout', json=payload, timeout=40).status_code == 200,
                    'Baseline order failed')
            payload = add(uid, sid, browser, 'unique-fault')
            index = 'sam_checkout_fault_' + secrets.token_hex(8)
            db.orders.create_index([('user_id', 1)], name=index, unique=True,
                                   partialFilterExpression={'user_id': uid})
            indexes.append(index)
            duplicate = dict(db.orders.find_one({'user_id': uid}))
            duplicate.update(_id=ObjectId(), order_number=marker + '-constraint-proof',
                             checkout_id=marker + '-constraint-proof')
            try:
                db.orders.insert_one(duplicate)
                raise RuntimeError('Database fault constraint did not reject duplicate')
            except DuplicateKeyError as error:
                require(error.code == 11000 and index in str(error), 'Unexpected duplicate constraint')
            before = snapshot(uid, sid)
            response = browser.post(base + '/checkout', json=payload, timeout=45)
            after = snapshot(uid, sid)
            require(response.status_code == 409 and before == after, 'Database fault leaked business writes')
            db.orders.drop_index(index); indexes.remove(index)
            recovery = browser.post(base + '/checkout', json=payload, timeout=40)
            replay = browser.post(base + '/checkout', json=payload, timeout=40)
            require(recovery.status_code == replay.status_code == 200
                    and recovery.json()['id'] == replay.json()['id'], 'Recovery replay failed')
            recovered = snapshot(uid, sid)
            require(recovered['orders'] == before['orders'] + 1
                    and recovered['items'] == before['items'] + 1
                    and recovered['stock'] == before['stock'] - 1, 'Recovery persistence mismatch')
            report['cases']['database_unique_write_error'] = {'mongo_error_code': 11000,
                'fault_point': 'orders.insert_one after SKU writes', 'http': response.status_code,
                'before': before, 'after': after, 'rollback_equal': before == after,
                'same_id_recovery_http': recovery.status_code, 'same_order_replay': True,
                'recovered': recovered, 'temporary_index_removed': True}

            uid, sid, browser = fixture('driver')
            payload = add(uid, sid, browser, 'driver')
            control = {'_id': marker + '-driver', 'probe_id': marker, 'user_id': uid,
                'phase': 'armed', 'mode': 'driver_error', 'expires_at': now + timedelta(minutes=10)}
            db.acceptance_probe_controls.insert_one(control)
            before = snapshot(uid, sid)
            response = browser.post(base + '/checkout', json=payload, timeout=45)
            after = snapshot(uid, sid)
            state = db.acceptance_probe_controls.find_one({'_id': control['_id']})
            require(state['phase'] == 'fault_injected' and response.status_code == 503
                    and before == after, 'Injected driver fault did not fully roll back')
            recovery = browser.post(base + '/checkout', json=payload, timeout=40)
            replay = browser.post(base + '/checkout', json=payload, timeout=40)
            require(recovery.status_code == replay.status_code == 200
                    and recovery.json()['id'] == replay.json()['id'], 'Driver-fault recovery failed')
            report['cases']['driver_error_after_order_item_writes'] = {'http': response.status_code,
                'injection': 'acceptance-only AutoReconnect exception; not an actual Atlas outage',
                'phase': state['phase'], 'before': before, 'after': after, 'rollback_equal': True,
                'same_id_recovery_http': recovery.status_code, 'same_order_replay': True}

        for change in ('session', 'disable'):
            uid, sid, browser = fixture(change)
            payload = add(uid, sid, browser, change)
            control = {'_id': marker + '-' + change, 'probe_id': marker, 'user_id': uid,
                'phase': 'armed', 'mode': 'pause', 'expires_at': datetime.now(timezone.utc) + timedelta(minutes=2)}
            db.acceptance_probe_controls.insert_one(control)
            before = snapshot(uid, sid)
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(browser.post, base + '/checkout', json=payload, timeout=55)
                try:
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        state = db.acceptance_probe_controls.find_one({'_id': control['_id']})
                        if state['phase'] == 'reached':
                            break
                        require(not pending.done(), 'Checkout completed before barrier')
                        time.sleep(.05)
                    require(state['phase'] == 'reached' and not pending.done(), 'Mid-transaction barrier unavailable')
                    if change == 'session':
                        require(db.auth_sessions.delete_many({'user_id': uid}).deleted_count == 1,
                                'Fixture session revoke failed')
                    else:
                        require(db.users.update_one({'_id': uid, 'acceptance_run': marker},
                            {'$set': {'status': 'inactive', 'is_active': False}}).modified_count == 1,
                            'Fixture account disable failed')
                    revoked_at = datetime.now(timezone.utc).isoformat()
                finally:
                    db.acceptance_probe_controls.update_one({'_id': control['_id']}, {'$set': {'phase': 'release'}})
                response = pending.result(timeout=60)
            after = snapshot(uid, sid)
            denied = browser.get(base + '/cart', allow_redirects=False, timeout=30)
            require(denied.status_code == 302, 'Subsequent revoked request was allowed')
            if config.get('baseline'):
                require(response.status_code == 200 and after['orders'] == before['orders'] + 1,
                        'Expected baseline race was not reproduced')
            else:
                require(response.status_code == 400 and before == after,
                        'Mid-transaction revocation did not roll back all business writes')
            report['cases']['inflight_' + change] = {'barrier': 'PURCHASE after stock/order/item writes',
                'barrier_reached_at': str(state['reached_at']), 'revoked_at': revoked_at,
                'http': response.status_code, 'before': before, 'after': after,
                'rollback_equal': before == after, 'next_request_denied_http': denied.status_code,
                'vulnerability_reproduced': bool(config.get('baseline'))}
        report['status'] = 'passed'
        report['acceptance_passed'] = not config.get('baseline')
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['error'] = str(error) if isinstance(error, RuntimeError) else 'Probe failed; details withheld'
    finally:
        for name in indexes:
            db.orders.drop_index(name)
        db.acceptance_probe_controls.delete_many({'probe_id': marker})
        report['cleanup'] = cleanup_transaction_probe(db, marker, users, skus, pid)
        report['cleanup']['controls_remaining'] = db.acceptance_probe_controls.count_documents({'probe_id': marker})
        report['cleanup']['temporary_indexes_remaining'] = sum(
            name.startswith('sam_checkout_fault_') for name in db.orders.index_information())
        report['cleanup']['verified'] = (report['cleanup']['verified']
            and report['cleanup']['controls_remaining'] == 0 and report['cleanup']['temporary_indexes_remaining'] == 0)
        if not report['cleanup']['verified']:
            report['status'] = 'cleanup_failed'
        client.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        raise SystemExit(1)
