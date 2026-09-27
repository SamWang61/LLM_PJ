"""Cart v3 overlays the immutable initial schema v2 migration."""
from copy import deepcopy
from pymongo import IndexModel
from bootstrap_schema import SCHEMAS as BASE_SCHEMAS, INDEXES as BASE_INDEXES
from bootstrap_schema import doc, obj, array, typ, string, integer, enum, OID, NOID, DATE, MONEY, NMONEY, HASH, two_decimals

SCHEMAS = deepcopy(BASE_SCHEMAS)
INDEXES = deepcopy(BASE_INDEXES)
SCHEMAS['carts'] = doc({
    'user_id': OID, 'status': enum('active', 'converted', 'abandoned'),
    'revision': integer(),
    'items': array(obj({'product_id': OID, 'quantity': integer(minimum=1, maximum=99),
                        'price_snapshot': MONEY, 'added_at': DATE, 'updated_at': DATE}), 20)
}, updated=True)
SCHEMAS['carts']['$jsonSchema']['properties']['schema_version']['enum'] = [3]
SCHEMAS['carts']['$and'] = [
    {'$expr': {'$eq': [{'$size': '$items'}, {'$size': {'$setUnion': ['$items.product_id', []]}}]}},
    {'$expr': {'$allElementsTrue': [{'$map': {'input':'$items', 'as':'i', 'in':two_decimals('$$i.price_snapshot')}}]}}
]
SCHEMAS['cart_events'] = doc({
    'cart_id': OID, 'user_id': OID, 'operation_id': string(128, minimum=1),
    'request_hash': HASH, 'event_type': string(40, minimum=1, pattern='^[A-Z][A-Z0-9_]*$'),
    'product_id': NOID, 'quantity_before': integer(True, maximum=99),
    'quantity_after': integer(True, maximum=99), 'price_snapshot': NMONEY,
    'event_at': DATE, 'metadata': typ('object')
})
SCHEMAS['cart_events']['$jsonSchema']['properties']['schema_version']['enum'] = [3]
item_fields = {'$and': [{'$ne':['$product_id',None]}, {'$ne':['$quantity_before',None]},
                         {'$ne':['$quantity_after',None]}, {'$ne':['$price_snapshot',None]}]}
def event_rule(event, rule):
    return {'$expr': {'$or': [{'$ne':['$event_type',event]}, rule]}}
SCHEMAS['cart_events']['$and'] = [
    {'$expr': two_decimals('$price_snapshot', True)},
    {'$expr': {'$lte':[{'$bsonSize':'$metadata'},2048]}},
    event_rule('ADD', {'$and':[item_fields, {'$gt':['$quantity_after','$quantity_before']}]}),
    event_rule('REMOVE', {'$and':[item_fields, {'$gt':['$quantity_before',0]}, {'$eq':['$quantity_after',0]}]}),
    event_rule('QTY_CHANGE', {'$and':[item_fields, {'$gt':['$quantity_before',0]},
                                     {'$gt':['$quantity_after',0]}, {'$ne':['$quantity_before','$quantity_after']}]}),
]
for kind in ('CHECKOUT','ABANDON'):
    SCHEMAS['cart_events']['$and'].append(event_rule(kind, {'$and':[
        {'$eq':['$'+field,None]} for field in ('product_id','quantity_before','quantity_after','price_snapshot')]}))
INDEXES['carts'] = [
    IndexModel([('user_id',1)], name='uq_carts_user_id_active', unique=True,
               partialFilterExpression={'status':'active'}),
    IndexModel([('user_id',1),('status',1)], name='idx_carts_user_id_status'),
    IndexModel([('status',1),('updated_at',1)], name='idx_carts_status_updated_at'),
    IndexModel([('updated_at',1)], name='idx_carts_updated_at'),
]
INDEXES['cart_events'] = [IndexModel([(field,1),('event_at',-1)], name=f'idx_cart_events_{field}_event_at')
                        for field in ('cart_id','user_id','event_type','product_id')]
INDEXES['cart_events'].append(IndexModel([('user_id',1),('operation_id',1)],
    name='uq_cart_events_user_id_operation_id', unique=True))


def verify_current(db):
    report=[]
    for name, validator in SCHEMAS.items():
        options=db[name].options()
        if options.get('validator') != validator or options.get('validationLevel') != 'strict' or options.get('validationAction') != 'error':
            raise RuntimeError(f'Validator mismatch: {name}')
        actual={i['name']:i for i in db[name].list_indexes()}
        if len(actual) != len(INDEXES[name])+1:
            raise RuntimeError(f'Index count mismatch: {name}')
        for model in INDEXES[name]:
            expected=model.document
            found=actual.get(expected['name'],{})
            for key,value in expected.items():
                if key=='key' and 'text' in value.values():
                    if found.get('weights') != {'name':1,'description':1}:
                        raise RuntimeError('Text index mismatch')
                elif found.get(key) != value:
                    raise RuntimeError(f'Index mismatch: {name}/{expected["name"]}/{key}')
        report.append({'collection':name,'count':db[name].count_documents({}),
                       'options':options,'indexes':list(actual.values())})
    return report
