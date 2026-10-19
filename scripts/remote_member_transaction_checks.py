"""Extra HTTP checks on registered, disposable private acceptance fixtures only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from bson import ObjectId
import requests
from remote_d4_consumer_probe import login, page, require, verify_scope
from remote_readonly_admin_checks import run as run_readonly_admin_checks


def csrf_headers(session, base):
    field = page(session, base + '/auth/logout').select_one('input[name="csrf_token"]')
    require(field and field.get('value'), 'CSRF unavailable')
    session.headers['X-CSRF-Token'] = field['value']
    return session


def replay_session(session):
    replay = requests.Session()
    replay.adapters.update(session.adapters)
    replay.headers.update(session.headers)
    replay.cookies.update(session.cookies)
    return replay


def scope(db, marker, user_ids, sku_ids, product_id):
    require(db.name == 'vibecart_acceptance_pr21', 'Deep probe database mismatch')
    for name, ids in (('users', user_ids), ('product_skus', sku_ids), ('products', [product_id])):
        require(ids and db[name].count_documents({'_id': {'$in': ids}, 'acceptance_run': marker}) == len(ids),
                'Deep probe fixture ownership mismatch')


def persisted_counts(db, user_ids, sku_ids):
    """Count dependent rows by their real keys, including orphan order items."""
    cart_ids = [row['_id'] for row in db.carts.find(
        {'user_id': {'$in': user_ids}}, {'_id': 1})]
    queries = {
        'orders': {'user_id': {'$in': user_ids}},
        # Current checkout writes user_id too. SKU ownership additionally
        # catches an anomalous item missing user_id or its parent order.
        'order_items': {'sku_id': {'$in': sku_ids}},
        'behavior_events': {'user_id': {'$in': user_ids}},
        'cart_events': {'cart_id': {'$in': cart_ids}},
    }
    return {name: db[name].count_documents(query) for name, query in queries.items()}


def run(db, config, marker, user_id, product_id, sku_id, email, password, user_ids, sku_ids, report):
    verify_scope(config)
    scope(db, marker, user_ids, sku_ids, product_id)
    base, token = config['service_url'].rstrip('/'), config['id_token']
    # Register identities before their first write so the caller can always clean them.
    admin_id, competitor_id = ObjectId(), ObjectId()
    user_ids.extend([admin_id, competitor_id])
    original = db.users.find_one({'_id': user_id, 'acceptance_run': marker})
    require(original, 'Probe customer missing')
    for uid, suffix, role in ((admin_id, 'admin', 'admin'), (competitor_id, 'competitor', 'customer')):
        db.users.insert_one({**original, '_id': uid, 'email': marker+'-'+suffix+'@example.invalid', 'role': role})
    scope(db, marker, user_ids, sku_ids, product_id)

    admin = login(base, token, marker+'-admin@example.invalid', password)
    require(admin.get(base+'/admin/', allow_redirects=False, timeout=30).status_code == 200,
            'Active administrator denied')
    no_csrf = admin.post(base+'/admin/summary', allow_redirects=False, timeout=30)
    require(no_csrf.status_code == 400, 'Admin mutation accepted without CSRF')
    run_readonly_admin_checks(db, config, admin, report)
    db.users.update_one({'_id': admin_id, 'acceptance_run': marker},
                        {'$set': {'status': 'inactive', 'is_active': False}})
    require(admin.get(base+'/admin/', allow_redirects=False, timeout=30).status_code == 302,
            'Inactive administrator cookie retained access')
    report['role_checks'] = {'active_admin_200': True, 'missing_csrf_400': True, 'inactive_admin_denied': True}

    first = csrf_headers(login(base, token, email, password), base)
    other = login(base, token, email, password)
    old_cookie = replay_session(first)
    field = page(first, base+'/auth/login').select_one('input[name="csrf_token"]')
    require(field and field.get('value'), 'Relogin CSRF missing')
    relogin = first.post(base+'/auth/login', data={'email': email, 'password': password,
        'csrf_token': field['value']}, allow_redirects=False, timeout=30)
    require(relogin.status_code in (302,303), 'Same-browser relogin failed')
    require(old_cookie.get(base+'/cart', allow_redirects=False, timeout=30).status_code == 302,
            'Cookie preceding relogin retained access')
    require(first.get(base+'/cart', timeout=30).status_code == 200
            and other.get(base+'/cart', timeout=30).status_code == 200, 'Relogin evicted another device')
    # This is the trusted maintainer's revoke-all interface, not a claim of a D5 UI.
    db.auth_sessions.delete_many({'user_id': user_id})
    require(first.get(base+'/cart', allow_redirects=False, timeout=30).status_code == 302
            and other.get(base+'/cart', allow_redirects=False, timeout=30).status_code == 302,
            'Revoked session retained access')
    disabled_first = login(base, token, email, password)
    disabled_other = login(base, token, email, password)
    db.users.update_one({'_id': user_id, 'acceptance_run': marker},
                        {'$set': {'status': 'inactive', 'is_active': False}})
    require(disabled_first.get(base+'/cart', allow_redirects=False, timeout=30).status_code == 302
            and disabled_other.get(base+'/cart', allow_redirects=False, timeout=30).status_code == 302,
            'Inactive customer retained device access')
    db.auth_sessions.delete_many({'user_id': user_id})
    db.users.update_one({'_id': user_id, 'acceptance_run': marker},
                        {'$set': {'status': 'active', 'is_active': True}})
    report['session_security'] = {'same_browser_relogin': True, 'old_cookie_denied': True,
        'other_device_preserved': True, 'maintainer_revoke_all_denied': True,
        'inactive_customer_both_devices_denied': True, 'd5_ui_tested': False}

    def add_cart(session, uid, sku, operation):
        csrf_headers(session, base)
        response = session.post(base+'/cart/add/'+str(product_id), json={
            'sku_id': str(sku), 'quantity': 1, 'operation_id': operation}, timeout=30)
        require(response.status_code == 200, 'Race/rollback cart add failed')
        cart = db.carts.find_one({'user_id': uid, 'status': 'active'})
        require(cart and cart['items'], 'Race/rollback cart readback missing')
        return cart

    race_first = login(base, token, email, password)
    race_second = login(base, token, marker+'-competitor@example.invalid', password)
    customers = [user_id, competitor_id]
    db.product_skus.update_one({'_id': sku_id, 'acceptance_run': marker},
        {'$set': {'stock_quantity': 1, 'available_quantity': 1, 'reserved_quantity': 0}})
    carts = [add_cart(s,uid,sku_id,marker+'-race-add-'+str(i))
             for i,(s,uid) in enumerate(zip((race_first,race_second),customers))]
    barrier = Barrier(2)
    def checkout(i):
        barrier.wait(timeout=15)
        return (race_first,race_second)[i].post(base+'/checkout', json={
            'cart_id': str(carts[i]['_id']), 'expected_revision': carts[i]['revision'],
            'checkout_id': marker+'-race-checkout-'+str(i)}, timeout=45).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(checkout,i) for i in range(2)]
        statuses = [f.result(timeout=60) for f in futures]
    require(statuses.count(200) == 1 and all(s in (200,400,409) for s in statuses),
            'Last-stock race did not produce one winner')
    require(db.product_skus.find_one({'_id': sku_id})['available_quantity'] == 0,
            'Last-stock race stock readback mismatch')
    require(db.orders.count_documents({'user_id': {'$in': customers}}) == 2,
            'Race persisted extra orders')  # Original happy path plus one race winner.
    report['last_stock_concurrency'] = {'parallel_clients': 2, 'http_statuses': statuses,
        'successful_checkouts': 1, 'stock_remaining': 0, 'orders_total_including_original': 2}

    loser = statuses.index(next(s for s in statuses if s != 200))
    loser_session = (race_first,race_second)[loser]
    blocked_id = ObjectId(); sku_ids.append(blocked_id)
    original_sku = db.product_skus.find_one({'_id': sku_id, 'acceptance_run': marker})
    db.product_skus.insert_one({**original_sku, '_id': blocked_id, 'sku_code': marker+'-blocked',
        'stock_quantity': 1, 'available_quantity': 1, 'reserved_quantity': 0})
    db.product_skus.update_one({'_id': sku_id, 'acceptance_run': marker},
        {'$set': {'stock_quantity': 1, 'available_quantity': 1}})
    cart = add_cart(loser_session, customers[loser], blocked_id, marker+'-rollback-add')
    require([i['sku_id'] for i in cart['items']] == [sku_id,blocked_id],
            'Rollback must fail after the first SKU mutation')
    scope(db, marker, user_ids, sku_ids, product_id)
    db.product_skus.update_one({'_id': blocked_id, 'acceptance_run': marker},
        {'$set': {'stock_quantity': 0, 'available_quantity': 0}})
    before = persisted_counts(db, customers, sku_ids)
    response = loser_session.post(base+'/checkout', json={'cart_id': str(cart['_id']),
        'expected_revision': cart['revision'], 'checkout_id': marker+'-rollback-checkout'},timeout=45)
    require(response.status_code in (400,409), 'Unavailable second SKU was not rejected')
    require(db.product_skus.find_one({'_id': sku_id})['available_quantity'] == 1,
            'First SKU mutation was not rolled back')
    require(db.carts.find_one({'_id':cart['_id']})['revision'] == cart['revision'],
            'Failed checkout changed cart revision')
    after = persisted_counts(db, customers, sku_ids)
    require(before == after and db.orders.count_documents({'checkout_id':marker+'-rollback-checkout'}) == 0,
            'Failed checkout left partial data')
    report['stock_failure_rollback'] = {'second_sku_unavailable_http':response.status_code,
        'first_sku_stock_preserved':True, 'cart_revision_preserved':True,
        'order_item_event_counts_unchanged':True, 'cart_event_counts_unchanged':True,
        'persisted_before':before, 'persisted_after':after,
        'order_items_scope':'fixture sku_id including orphan items',
        'arbitrary_fault_injection_tested':False}
