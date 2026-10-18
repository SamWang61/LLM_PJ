"""H05 cart persistence and H07 event contract on caller-owned private fixtures."""
from remote_d4_consumer_probe import page, require


def cart_checks(db, session, base, marker, user_id, product_id, sku_id):
    require(db.name == 'vibecart_acceptance_pr21', 'H05 database scope mismatch')
    for name, ident in (('users', user_id), ('products', product_id), ('product_skus', sku_id)):
        require(db[name].count_documents({'_id': ident, 'acceptance_run': marker}) == 1,
                'H05 fixture ownership mismatch')
    # Real GET routes create SEARCH/PRODUCT_VIEW; no event is synthesized here.
    page(session, base + '/?q=' + marker)
    page(session, base + '/product/' + str(product_id))
    statuses, revisions = [], []

    def mutate(route, quantity, operation, revision=None):
        data = {'operation_id': marker + operation}
        if quantity is not None:
            data['quantity'] = quantity
        if revision is not None:
            data['expected_revision'] = revision
        if route.startswith('/cart/add/'):
            data['sku_id'] = str(sku_id)
        response = session.post(base + route, json=data, timeout=45)
        statuses.append(response.status_code)
        require(response.status_code == 200, 'H05 cart mutation failed')
        cart = db.carts.find_one({'user_id': user_id, 'status': 'active'})
        require(cart, 'H05 persisted cart missing')
        revisions.append(cart['revision'])
        return cart

    cart = mutate('/cart/add/' + str(product_id), 2, '-h05-add')
    require(len(cart['items']) == 1 and cart['items'][0]['quantity'] == 2,
            'H05 add-two persistence mismatch')
    cart = mutate('/cart/update/' + str(sku_id), 1, '-h05-update', cart['revision'])
    page(session, base + '/cart')
    cart = db.carts.find_one({'_id': cart['_id']})
    require(len(cart['items']) == 1 and cart['items'][0]['quantity'] == 1,
            'H05 reload-one persistence mismatch')
    before = cart
    event_count = db.cart_events.count_documents({'cart_id': cart['_id']})
    stale = session.post(base + '/cart/update/' + str(sku_id), json={
        'quantity': 2, 'operation_id': marker + '-h05-stale',
        'expected_revision': revisions[0]}, timeout=45)
    require(stale.status_code == 409
            and db.carts.find_one({'_id': cart['_id']}) == before
            and db.cart_events.count_documents({'cart_id': cart['_id']}) == event_count,
            'H05 stale revision changed persisted cart')
    cart = mutate('/cart/remove/' + str(sku_id), None, '-h05-remove', cart['revision'])
    page(session, base + '/cart')
    require(db.carts.find_one({'_id': cart['_id']})['items'] == [],
            'H05 removed item returned after reload')
    cart = mutate('/cart/add/' + str(product_id), 1, '-h05-checkout-add', cart['revision'])
    require(revisions == sorted(set(revisions)) and cart['items'][0]['quantity'] == 1,
            'H05 revision sequence mismatch')
    return cart, {'status': 'passed', 'add_two_update_one_reload_remove_reload': True,
                  'http_statuses': statuses, 'revision_sequence': revisions,
                  'stale_revision_http': stale.status_code, 'stale_state_unchanged': True,
                  'readded_for_checkout_quantity': 1}


def event_checks(db, user_id, product_id, cart_id, order_id, marker):
    events = list(db.behavior_events.find({'user_id': user_id}))
    types = ('SEARCH', 'PRODUCT_VIEW', 'ADD_TO_CART', 'PURCHASE')
    counts = {kind: sum(e['event_type'] == kind for e in events) for kind in types}
    require(all(counts.values()), 'H07 four event types missing')
    require(all(e.get('schema_version') == 4 and e.get('event_id')
                and e.get('session_id') and e.get('event_at') for e in events),
            'H07 required event fields missing')
    require(len({e['event_id'] for e in events}) == len(events), 'H07 duplicate event IDs')
    require(any(e['event_type'] == 'SEARCH' and e.get('search_query') == marker for e in events),
            'H07 search query linkage missing')
    require(any(e['event_type'] == 'PRODUCT_VIEW' and e.get('product_id') == product_id for e in events),
            'H07 product linkage missing')
    purchases = [e for e in events if e['event_type'] == 'PURCHASE']
    require(len(purchases) == 1 and purchases[0].get('order_id') == order_id
            and purchases[0].get('cart_id') == cart_id
            and purchases[0].get('metadata', {}).get('exclude_from_attribution') is True,
            'H07 demo purchase linkage/attribution exclusion missing')
    return {'status': 'passed', 'event_type_counts': counts, 'unique_event_ids': True,
            'required_contract_fields': True, 'search_product_order_cart_links': True,
            'demo_purchase_excluded_from_attribution': True,
            'readback_scope': 'new disposable private user; real HTTPS-generated events'}
