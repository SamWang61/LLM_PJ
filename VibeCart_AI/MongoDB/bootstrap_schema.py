"""Initialize schema v2 in the verified, initially empty VibeCart Atlas database.

Not a legacy-data migration. Credentials are read from .env.schema, never logged.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

from bson import Decimal128, json_util
from dotenv import dotenv_values
from pymongo import MongoClient, IndexModel

ROOT = Path(__file__).resolve().parent
HOST = 'vibecart-ai-free.odqe25w.mongodb.net'
MIGRATION = '20260916_01_initial_schema_v2'


def typ(t, nullable=False, **kw):
    return {'bsonType': [t, 'null'] if nullable else t, **kw}


def string(maximum=None, nullable=False, minimum=None, **kw):
    if maximum is not None:
        kw['maxLength'] = maximum
    if minimum is not None:
        kw['minLength'] = minimum
    return typ('string', nullable, **kw)


def integer(nullable=False, minimum=0, **kw):
    return typ('int', nullable, minimum=minimum, **kw)


def enum(*values):
    return {'enum': list(values)}


def array(items, maximum, minimum=0, unique=False):
    return {'bsonType': 'array', 'items': items, 'minItems': minimum,
            'maxItems': maximum, 'uniqueItems': unique}


def obj(properties):
    return {'bsonType': 'object', 'required': list(properties),
            'properties': properties, 'additionalProperties': False}


def doc(properties, string_id=False, timestamps=True, updated=False):
    fields = {'_id': string(minimum=1) if string_id else typ('objectId'),
              'schema_version': typ('int', enum=[2]), **properties}
    if timestamps:
        fields['created_at'] = typ('date')
    if updated:
        fields['updated_at'] = typ('date')
    return {'$jsonSchema': obj(fields)}


OID = typ('objectId')
NOID = typ('objectId', True)
DATE = typ('date')
NDATE = typ('date', True)
BOOL = typ('bool')
MONEY = typ('decimal', minimum=Decimal128('0'))
NMONEY = typ('decimal', True, minimum=Decimal128('0'))
TAGS = array(string(30, minimum=1), 20, unique=True)
HASH = string(64, minimum=64, pattern='^[a-f0-9]{64}$')
FREE_OBJECT = typ('object')
PROVIDERS = ('huggingface', 'anthropic', 'rules', 'pipeline')
EVENTS = ('product_view', 'product_search', 'add_to_cart', 'remove_from_cart',
          'purchase', 'recommendation_impression', 'recommendation_click')
FINITE_DOUBLE = typ('double', minimum=-sys.float_info.max, maximum=sys.float_info.max)

SCHEMAS = {}
SCHEMAS['users'] = doc({
    'display_name': string(100, minimum=1), 'email': string(minimum=1, pattern=r'^[^\sA-Z]+$'),
    'auth_provider': enum('local'), 'password_hash': string(minimum=1),
    'firebase_uid': string(nullable=True), 'role': enum('customer', 'admin'),
    'is_active': BOOL, 'preferences': obj({
        'category_ids': array(OID, 10, unique=True), 'tags': TAGS,
        'budget_min': NMONEY, 'budget_max': NMONEY, 'updated_at': NDATE
    })}, updated=True)
SCHEMAS['categories'] = doc({
    'name': string(100, minimum=1), 'slug': string(100, minimum=1, pattern='^[a-z0-9-]+$'),
    'description': string(1000, True), 'sort_order': integer(), 'is_active': BOOL
}, updated=True)
SCHEMAS['products'] = doc({
    'category_id': OID, 'name': string(200, minimum=1), 'description': string(5000, minimum=1),
    'sku': string(64, minimum=1, pattern=r'^[^a-z\s]+$'),
    'brand': string(100, True), 'size': string(100, True), 'color': string(100, True),
    'price': MONEY, 'sale_price': NMONEY, 'currency': enum('TWD'),
    'stock_quantity': integer(), 'safety_stock': integer(), 'tags': TAGS,
    'image_urls': array(string(pattern=r'^(https://|/(?!/))'), 10), 'is_active': BOOL
}, updated=True)
SCHEMAS['carts'] = doc({'user_id': OID, 'items': array(obj({
    'product_id': OID, 'quantity': integer(minimum=1, maximum=99), 'added_at': DATE
}), 20)}, updated=True)
SCHEMAS['orders'] = doc({
    'order_number': string(minimum=1), 'user_id': OID, 'checkout_id': string(minimum=1),
    'request_hash': HASH, 'status': enum('pending', 'confirmed', 'shipping', 'completed', 'cancelled'),
    'payment_status': enum('unpaid', 'paid', 'failed', 'refunded'), 'is_demo': BOOL,
    'currency': enum('TWD'), 'items': array(obj({
        'product_id': OID, 'product_name': string(200, minimum=1), 'sku': string(64, minimum=1),
        'size': string(100, True), 'color': string(100, True), 'unit_price': MONEY,
        'quantity': integer(minimum=1, maximum=99), 'subtotal_amount': MONEY
    }), 20, 1), 'subtotal_amount': MONEY, 'discount_amount': MONEY,
    'shipping_fee': MONEY, 'total_amount': MONEY, 'shipping_address': typ('null'),
    'paid_at': NDATE
}, updated=True)
SCHEMAS['user_events'] = doc({
    'event_id': string(minimum=1), 'user_id': NOID, 'session_id': string(128, minimum=1),
    'event_type': enum(*EVENTS), 'product_id': NOID, 'order_id': NOID,
    'recommendation_id': NOID, 'search_query': string(200, True, 1),
    'event_metadata': FREE_OBJECT
})
SCHEMAS['ai_requests'] = doc({
    'user_id': NOID, 'parent_request_id': NOID,
    'task_type': enum('product_embedding', 'product_recommendation', 'sales_summary'),
    'execution_mode': enum('local', 'api', 'hybrid', 'baseline'),
    'requested_provider': enum(*PROVIDERS), 'actual_provider': enum(*PROVIDERS, None),
    'model_name': string(nullable=True), 'model_revision': string(nullable=True),
    'prompt_name': string(nullable=True), 'prompt_version': string(nullable=True),
    'status': enum('queued', 'running', 'succeeded', 'failed', 'timeout'),
    'is_success': typ('bool', True), 'input_text': string(8000, True), 'output_text': string(8000, True),
    'input_summary': FREE_OBJECT, 'parameters': FREE_OBJECT, 'latency_ms': integer(True),
    'input_tokens': integer(True), 'output_tokens': integer(True), 'token_count': integer(True),
    'estimated_cost': NMONEY, 'cost_currency': enum('USD', None), 'is_cache_hit': BOOL,
    'fallback_reason': string(nullable=True), 'error_code': string(nullable=True),
    'started_at': NDATE, 'completed_at': NDATE
})
SCHEMAS['product_embeddings'] = doc({
    'product_id': OID, 'model': enum('BAAI/bge-small-zh-v1.5'),
    'revision': string(minimum=1), 'vector': array(FINITE_DOUBLE, 512, 512),
    'dimension': typ('int', enum=[512]), 'content_hash': HASH,
    'preprocessing_version': string(minimum=1), 'is_normalized': BOOL
}, updated=True)
SCHEMAS['recommendations'] = doc({
    'user_id': NOID, 'session_id': string(128, minimum=1), 'source_product_id': NOID,
    'ai_request_id': OID, 'strategy': enum('baseline', 'bge_similar', 'bge_personalized'),
    'model': string(nullable=True), 'revision': string(nullable=True),
    'items': array(obj({'product_id': OID, 'rank': integer(minimum=1, maximum=10),
                        'score': FINITE_DOUBLE, 'reason': string(500, minimum=1)}), 10)
})
SCHEMAS['ai_insights'] = doc({
    'ai_request_id': OID, 'task_type': enum('sales_summary'),
    'period_start': DATE, 'period_end': DATE, 'report_timezone': enum('Asia/Taipei'),
    'is_demo': enum(True), 'input_summary': FREE_OBJECT, 'text': string(8000, minimum=1),
    'model': string(minimum=1), 'prompt_version': string(minimum=1), 'usage': FREE_OBJECT,
    'elapsed_ms': integer(True), 'expires_at': DATE
}, string_id=True)
SCHEMAS['ai_usage'] = doc({'count': integer(), 'updated_at': DATE}, string_id=True, timestamps=False)
SCHEMAS['request_limits'] = doc({'count': integer(), 'expires_at': DATE}, string_id=True, timestamps=False)
SCHEMAS['schema_migrations'] = doc({
    'checksum': HASH, 'status': enum('running', 'succeeded', 'failed'),
    'started_at': DATE, 'completed_at': NDATE,
    'counts': obj({'source': integer(), 'target': integer(), 'errors': integer()}),
    'error_code': string(nullable=True)
}, string_id=True, timestamps=False)


def constraint(name, expression):
    SCHEMAS[name].setdefault('$and', []).append({'$expr': expression})


def two_decimals(field, nullable=False):
    check = {'$and': [{'$lte': [field, Decimal128('1E+6144')]},
                      {'$eq': [field, {'$round': [field, 2]}]}]}
    return {'$or': [{'$eq': [field, None]}, check]} if nullable else check


constraint('users', {'$or': [{'$eq': ['$preferences.budget_min', None]},
                           {'$eq': ['$preferences.budget_max', None]},
                           {'$lte': ['$preferences.budget_min', '$preferences.budget_max']}]})
for field in ('price', 'sale_price'):
    constraint('products', two_decimals('$' + field, field == 'sale_price'))
constraint('products', {'$or': [{'$eq': ['$sale_price', None]}, {'$lte': ['$sale_price', '$price']}]})
for name in ('carts', 'orders', 'recommendations'):
    constraint(name, {'$eq': [{'$size': '$items'}, {'$size': {'$setUnion': ['$items.product_id', []]}}]})
for field in ('subtotal_amount', 'discount_amount', 'shipping_fee', 'total_amount'):
    constraint('orders', two_decimals('$' + field))
constraint('orders', {'$lte': ['$discount_amount', '$subtotal_amount']})
constraint('orders', {'$eq': ['$shipping_fee', Decimal128('0')]})
constraint('orders', {'$eq': ['$subtotal_amount', {'$sum': '$items.subtotal_amount'}]})
constraint('orders', {'$eq': ['$total_amount', {'$add': [{'$subtract': ['$subtotal_amount', '$discount_amount']}, '$shipping_fee']}]})
constraint('orders', {'$allElementsTrue': [{'$map': {'input': '$items', 'as': 'i', 'in': {
    '$and': [two_decimals('$$i.unit_price'), {'$eq': ['$$i.subtotal_amount', {'$multiply': ['$$i.unit_price', '$$i.quantity']}]}]
}}}]})
constraint('orders', {'$or': [{'$ne': ['$payment_status', 'paid']}, {'$ne': ['$paid_at', None]}]})
for values, field in [(('product_view', 'add_to_cart', 'remove_from_cart'), 'product_id'),
                      (('purchase',), 'order_id'),
                      (('recommendation_impression', 'recommendation_click'), 'recommendation_id'),
                      (('product_search',), 'search_query')]:
    constraint('user_events', {'$or': [{'$not': [{'$in': ['$event_type', list(values)]}]}, {'$ne': ['$' + field, None]}]})
constraint('product_embeddings', {'$anyElementTrue': [{'$map': {'input': '$vector', 'as': 'v', 'in': {'$ne': ['$$v', 0]}}}]})
constraint('recommendations', {'$eq': ['$items.rank', {'$range': [1, {'$add': [{'$size': '$items'}, 1]}]}]})
score_bounds = {'$and': [{'$gte': ['$$i.score', -1]}, {'$lte': ['$$i.score', 1]}]}
valid_scores = {'$allElementsTrue': [{'$map': {'input': '$items', 'as': 'i', 'in': score_bounds}}]}
constraint('recommendations', {'$or': [
    {'$eq': ['$strategy', 'baseline']},
    {'$and': [{'$ne': ['$model', None]}, {'$ne': ['$revision', None]}, valid_scores]}
]})
constraint('recommendations', {'$or': [{'$ne': ['$strategy', 'bge_similar']}, {'$ne': ['$source_product_id', None]}]})
constraint('ai_insights', {'$lt': ['$period_start', '$period_end']})
for collection, field, size in [('user_events', 'event_metadata', 2048), ('ai_requests', 'input_summary', 8192), ('ai_insights', 'input_summary', 8192)]:
    constraint(collection, {'$lte': [{'$bsonSize': '$' + field}, size]})
constraint('ai_requests', {'$or': [
    {'$and': [{'$in': ['$status', ['queued', 'running']]}, {'$eq': ['$is_success', None]}]},
    {'$and': [{'$in': ['$status', ['succeeded', 'failed', 'timeout']]},
              {'$eq': ['$is_success', {'$eq': ['$status', 'succeeded']}]},
              {'$ne': ['$latency_ms', None]}, {'$ne': ['$completed_at', None]}]}
]})
constraint('ai_requests', {'$or': [{'$eq': ['$estimated_cost', None]}, {'$eq': ['$cost_currency', 'USD']}]})

INDEXES = {name: [] for name in SCHEMAS}


def index(collection, keys, name, **options):
    INDEXES[collection].append(IndexModel(keys, name=name, **options))


for collection, field in [('users','email'), ('categories','name'), ('categories','slug'),
                          ('products','sku'), ('carts','user_id'), ('orders','order_number'), ('user_events','event_id')]:
    index(collection, [(field,1)], f'uq_{collection}_{field}', unique=True)
index('users', [('firebase_uid',1)], 'uq_users_firebase_uid', unique=True,
      partialFilterExpression={'firebase_uid': {'$type':'string'}})
index('products', [('name','text'), ('description','text')], 'idx_products_name_description_text', default_language='none')
index('orders', [('user_id',1),('checkout_id',1)], 'uq_orders_user_id_checkout_id', unique=True)
index('user_events', [('order_id',1)], 'uq_user_events_order_id_purchase', unique=True,
      partialFilterExpression={'event_type':'purchase','order_id':{'$type':'objectId'}})
index('product_embeddings', [('product_id',1),('model',1)], 'uq_product_embeddings_product_id_model', unique=True)
for collection, keys in [
    ('products', [('category_id',1),('is_active',1)]),
    ('orders', [('user_id',1),('created_at',-1)]),
    ('orders', [('is_demo',1),('payment_status',1),('created_at',-1)]),
    ('orders', [('status',1),('created_at',-1)]),
    ('user_events', [('user_id',1),('event_type',1),('created_at',-1)]),
    ('user_events', [('recommendation_id',1),('event_type',1)]),
    ('recommendations', [('user_id',1),('created_at',-1)]),
    ('ai_requests', [('task_type',1),('actual_provider',1),('created_at',-1)]),
    ('ai_requests', [('parent_request_id',1)])]:
    index(collection, keys, 'idx_' + collection + '_' + '_'.join(k for k,v in keys))
for collection in ('ai_insights','request_limits'):
    index(collection, [('expires_at',1)], f'ttl_{collection}_expires_at', expireAfterSeconds=0)


def connect(filename='.env.schema'):
    from urllib.parse import urlparse
    config = dotenv_values(ROOT / filename)
    uri = config['MONGO_URI']
    assert urlparse(uri).hostname == HOST and config['MONGO_DB'] == 'vibecart_ai', 'Unexpected target'
    client = MongoClient(uri, serverSelectionTimeoutMS=20000, tz_aware=True, maxPoolSize=5)
    client.vibecart_ai.command('ping')
    return client


def verify(db):
    report = []
    for name, validator in SCHEMAS.items():
        opts = db[name].options()
        assert opts.get('validator') == validator, f'Validator mismatch: {name}'
        assert opts.get('validationLevel') == 'strict' and opts.get('validationAction') == 'error'
        actual = {i['name']: i for i in db[name].list_indexes()}
        assert len(actual) == len(INDEXES[name]) + 1, f'Unexpected indexes: {name}'
        for model in INDEXES[name]:
            expected = model.document
            found = actual[expected['name']]
            for key, value in expected.items():
                if key == 'key' and any(v == 'text' for v in value.values()):
                    assert found['weights'] == {'description': 1, 'name': 1}
                else:
                    assert found.get(key) == value, f'Index mismatch: {name}/{key}'
        report.append({'collection': name, 'count': db[name].count_documents({}),
                       'options': opts, 'indexes': list(actual.values())})
    return report


def main():
    checksum = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with connect() as client:
        db = client.vibecart_ai
        present = set(db.list_collection_names())
        assert not (present - set(SCHEMAS)), 'Unexpected collections; review manually'
        record = db.schema_migrations.find_one({'_id': MIGRATION})
        if record:
            assert record['checksum'] == checksum, 'Migration checksum mismatch'
            assert record['status'] == 'succeeded', 'Partial migration requires review'
        else:
            assert all(db[n].count_documents({}) == 0 for n in present), 'Nonempty database; use migration workflow'
            for name, validator in SCHEMAS.items():
                if name not in present:
                    db.create_collection(name, validator=validator, validationLevel='strict', validationAction='error')
                else:
                    assert db[name].options().get('validator') == validator, 'Existing validator differs'
            started = datetime.now(timezone.utc)
            db.schema_migrations.insert_one({'_id':MIGRATION, 'schema_version':2,
                'checksum':checksum, 'status':'running', 'started_at':started,
                'completed_at':None, 'counts':{'source':0,'target':0,'errors':0}, 'error_code':None})
            try:
                for name, indexes in INDEXES.items():
                    if indexes:
                        db[name].create_indexes(indexes)
                verify(db)
                db.schema_migrations.update_one({'_id':MIGRATION}, {'$set':{
                    'status':'succeeded', 'completed_at':datetime.now(timezone.utc),
                    'counts':{'source':0,'target':0,'errors':0}}})
            except Exception as exc:
                db.schema_migrations.update_one({'_id':MIGRATION}, {'$set':{
                    'status':'failed','completed_at':datetime.now(timezone.utc),
                    'error_code':type(exc).__name__, 'counts':{'source':0,'target':0,'errors':1}}})
                raise
        report = verify(db)
        payload = {'checked_at':datetime.now(timezone.utc), 'host':HOST,
                   'database':'vibecart_ai', 'migration':db.schema_migrations.find_one({'_id':MIGRATION}),
                   'collections':report}
        (ROOT / '05_實際Schema與索引.md').write_text(
            '# Atlas 實際 Schema 與索引讀回\n\n此內容由 PyMongo 從目標資料庫讀回；不含憑證。\n\n```json\n'
            + json_util.dumps(payload, indent=2, ensure_ascii=False) + '\n```\n', encoding='utf-8')
        print(json.dumps({'collections':len(report), 'custom_indexes':sum(len(v) for v in INDEXES.values()),
                          'validators':'strict/error', 'migration':'succeeded'}))


if __name__ == '__main__':
    main()
