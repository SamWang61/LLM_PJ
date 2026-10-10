"""D5 audit schema proposal, NOT deployed or part of schema_active_v4.

Business snapshots are resource-specific allowlists. Audit TTL is not an
idempotency lifetime. Index uniqueness deliberately waits for batch semantics.
"""
from pymongo import IndexModel
from bootstrap_schema import obj, OID, DATE, string, enum, BOOL, MONEY, integer

MIGRATION_PROPOSAL = '20261011_06_admin_audit_v1'
FIELDS = {
    'product': {'product_name': string(200, minimum=1), 'description': string(5000, minimum=1),
                'status': enum('active', 'inactive', 'draft'), 'is_ai_recommendable': BOOL},
    'sku': {'price': MONEY, 'stock_quantity': integer(), 'status': enum('active', 'inactive'),
            'available_quantity': integer(), 'stock_status': enum('in_stock', 'low_stock', 'out_of_stock')},
    'order': {'status': enum('pending', 'confirmed', 'shipping', 'completed', 'cancelled')},
    'customer': {'status': enum('active', 'inactive'), 'is_active': {'bsonType': 'bool'}},
}


def snapshot(fields):
    shape = obj(fields)
    shape['required'] = []  # A patch contains only the fields that actually changed.
    shape['minProperties'] = 1
    return shape


VALIDATOR = {'$jsonSchema': obj({
    '_id': OID, 'actor_id': OID, 'request_id': string(128, minimum=1),
    'resource_type': enum(*FIELDS), 'resource_id': OID,
    'before': {'bsonType': 'object'}, 'after': {'bsonType': 'object'},
    'reason': string(500, minimum=1), 'result': enum('succeeded'), 'created_at': DATE,
})}
# Conditional validators prevent password/token/URI or unrelated fields entering snapshots.
VALIDATOR['$or'] = [
    {'resource_type': kind, 'before': {'$exists': True},
     '$jsonSchema': {'properties': {'before': snapshot(fields), 'after': snapshot(fields)}}}
    for kind, fields in FIELDS.items()
]
INDEXES = [IndexModel([('created_at', 1)], name='admin_audit_retention_180d', expireAfterSeconds=180 * 86400),
           IndexModel([('resource_type', 1), ('resource_id', 1), ('created_at', -1)], name='admin_audit_resource'),
           IndexModel([('actor_id', 1), ('request_id', 1)], name='admin_audit_request')]
