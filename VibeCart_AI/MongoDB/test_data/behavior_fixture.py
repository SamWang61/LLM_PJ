"""D4 offline fixtures. No connection, writes, attribution or score processing."""
import hashlib
from collections import Counter
from datetime import timedelta, timezone
from bson import ObjectId, BSON

BATCH = 'sam-behavior-20261011-v1'
SOURCE_BATCH = 'sam-synthetic-20261005-v1'
WEIGHTS = {'PURCHASE': 4, 'ADD_TO_CART': 3, 'SEARCH': 2, 'PRODUCT_VIEW': 1}


def utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def references(data, catalog):
    return ({o['_id']: o for o in data['orders']},
            {u['_id']: u for u in data['users']},
            {p['_id']: p for p in catalog['products']})


def build(data, catalog, max_orders=100):
    if isinstance(max_orders, bool) or not isinstance(max_orders, int) or not 1 <= max_orders <= 1000:
        raise ValueError('max_orders must be 1..1000')
    orders, users, products = references(data, catalog)
    candidates = [o for o in orders.values() if o.get('synthetic_batch_id') == SOURCE_BATCH
                  and o.get('is_demo') is True and o.get('payment_status') == 'paid'
                  and o.get('status') != 'cancelled']
    candidates.sort(key=lambda o: (utc(o['ordered_at']), str(o['_id'])))
    selected = {o['_id'] for o in candidates[:max_orders]}
    items = sorted((i for i in data['order_items'] if i['order_id'] in selected), key=lambda i: str(i['_id']))
    result = []
    for item in items:
        order, product = orders[item['order_id']], products[item['product_id']]
        if item['user_id'] != order['user_id'] or order['user_id'] not in users:
            raise ValueError('Broken source user reference')
        # No invented pre-purchase journey: all four synthetic exercises occur
        # at/after this order, and after registration, never before either.
        start = max(utc(order['ordered_at']), utc(users[order['user_id']]['registered_at']))
        for offset, kind in enumerate(('PRODUCT_VIEW', 'SEARCH', 'ADD_TO_CART', 'PURCHASE')):
            event_id = f'{BATCH}:{item["_id"]}:{kind}'
            at = start + timedelta(seconds=offset)
            result.append({
                '_id': ObjectId(hashlib.sha256(event_id.encode()).hexdigest()[:24]),
                'schema_version': 4, 'event_id': event_id, 'user_id': order['user_id'],
                'anonymous_id': None, 'session_id': f'{BATCH}:{order["_id"]}',
                'event_type': kind, 'product_id': product['_id'],
                'major_category_id': product['major_category_id'], 'minor_category_id': product['minor_category_id'],
                'quantity': item['quantity'] if kind == 'PURCHASE' else 1,
                'order_id': order['_id'] if kind == 'PURCHASE' else None,
                'cart_id': None, 'search_query': 'synthetic catalog search' if kind == 'SEARCH' else None,
                'source': 'sam_synthetic_fixture', 'recommendation_id': None,
                'event_at': at, 'created_at': at, 'score_version': 1, 'processed_at': None,
                'metadata': {'synthetic': True, 'synthetic_batch_id': BATCH,
                             'source_batch_id': SOURCE_BATCH, 'order_item_id': str(item['_id']),
                             'exclude_from_attribution': True},
            })
    if not result:
        raise ValueError('No eligible demo order items')
    validate(result, data, catalog)
    return result


def validate(events, data, catalog):
    orders, users, products = references(data, catalog)
    items = {str(i['_id']): i for i in data['order_items']}
    ids, object_ids = set(), set()
    for e in events:
        def require(condition, label):
            if not condition:
                raise ValueError(label)
        require(e['event_id'] not in ids and e['_id'] not in object_ids, 'Duplicate event')
        ids.add(e['event_id']); object_ids.add(e['_id'])
        meta = e['metadata']
        require(meta.get('synthetic') is True and meta.get('synthetic_batch_id') == BATCH
                and meta.get('source_batch_id') == SOURCE_BATCH
                and meta.get('exclude_from_attribution') is True, 'Synthetic isolation missing')
        require(len(BSON.encode(meta)) <= 2048, 'Metadata too large')
        require(e['recommendation_id'] is None and e['processed_at'] is None, 'Attribution/processing forbidden')
        require(e['source'] == 'sam_synthetic_fixture' and e['event_type'] in WEIGHTS, 'Invalid event')
        require(e['user_id'] in users and e['product_id'] in products, 'Broken reference')
        item = items.get(meta.get('order_item_id'))
        require(item is not None, 'Broken item reference')
        order = orders.get(item['order_id'])
        require(order is not None and order.get('synthetic_batch_id') == SOURCE_BATCH
                and order.get('is_demo') is True and order.get('payment_status') == 'paid'
                and order.get('status') != 'cancelled', 'Ineligible order')
        require(item['user_id'] == order['user_id'] == e['user_id']
                and item['product_id'] == e['product_id'], 'Item mismatch')
        product = products[e['product_id']]
        require(all(e[k] == product[k] for k in ('major_category_id', 'minor_category_id')), 'Category mismatch')
        require(utc(e['event_at']) >= max(utc(order['ordered_at']), utc(users[e['user_id']]['registered_at'])), 'Invalid chronology')
        require(e['quantity'] == (item['quantity'] if e['event_type'] == 'PURCHASE' else 1), 'Quantity mismatch')
        require(e['order_id'] == (order['_id'] if e['event_type'] == 'PURCHASE' else None), 'Order mismatch')
        require(e['search_query'] == ('synthetic catalog search' if e['event_type'] == 'SEARCH' else None), 'Search mismatch')


def expected(events):
    counts = Counter(e['event_type'] for e in events)
    return {'batch': BATCH, 'source_batch': SOURCE_BATCH, 'events': len(events),
            'counts': dict(sorted(counts.items())), 'weights': WEIGHTS,
            'weighted_event_count': sum(WEIGHTS[k] * n for k, n in counts.items()),
            'production_attribution_events': 0, 'database_writes': 0,
            'note': 'Offline exercise counts; not production scores or conversion performance.'}
