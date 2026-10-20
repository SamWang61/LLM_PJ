"""Additive D5 v1.2 contract. Not activated in schema_active_v4 until rollout."""
from pymongo import IndexModel
from bootstrap_schema import obj, OID, DATE, string, enum, BOOL, MONEY, integer

MIGRATION = '20261018_07_admin_audit_receipts_v4'
RETENTION_SECONDS = 180 * 86400
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
REQUEST_ID = string(64, pattern='^'+UUID+r'(?::(?:[0-9]|[1-9][0-9]))?$')
FIELDS = {
    'product': {'product_name': string(200, minimum=1), 'description': string(5000, minimum=1),
                'status': enum('active','inactive','draft'), 'is_ai_recommendable': BOOL},
    'sku': {'price': MONEY, 'stock_quantity': integer(), 'status': enum('active','inactive'),
            'available_quantity': integer(), 'stock_status': enum('in_stock','low_stock','out_of_stock')},
    'order': {'status': enum('pending','confirmed','shipping','completed','cancelled')},
    'customer': {'status': enum('active','inactive'), 'is_active': BOOL},
}


def snapshot(fields):
    shape=obj(fields);shape.pop('required',None);shape['minProperties']=1
    return shape


AUDIT = {'$jsonSchema': obj({'_id': OID, 'schema_version': {'bsonType':'int','enum':[4]},
    'actor_id': OID, 'request_id': REQUEST_ID, 'resource_type': enum(*FIELDS), 'resource_id': OID,
    'before': {'bsonType':'object'}, 'after': {'bsonType':'object'},
    'reason': string(500,minimum=1), 'result': enum('succeeded'), 'created_at': DATE})}
AUDIT['$or']=[{'resource_type':kind,'$jsonSchema':{'properties':{
    'before':snapshot(fields),'after':snapshot(fields)}}} for kind,fields in FIELDS.items()]

ITEM = obj({'index': integer(maximum=99), 'resource_type': enum(*FIELDS), 'resource_id': OID,
            'status': enum('succeeded','rejected'), 'http_status': integer(minimum=200,maximum=599)})
RESULT = obj({'status': enum('succeeded','rejected'),
              'http_status': integer(minimum=200,maximum=599),
              'items': {'bsonType':'array','items':ITEM,'maxItems':100}})
RECEIPT = {'$jsonSchema': obj({'_id': OID, 'schema_version': {'bsonType':'int','enum':[4]},
    'actor_id': OID, 'request_id': REQUEST_ID, 'request_hash': string(64,pattern='^[a-f0-9]{64}$'),
    'mode': enum('single','atomic','per_item'), 'result': RESULT,
    'created_at': DATE, 'expires_at': DATE}),
    '$expr': {'$eq':['$expires_at',{'$add':['$created_at',RETENTION_SECONDS*1000]}]}}
SCHEMAS={'admin_audit_logs':AUDIT,'admin_write_requests':RECEIPT}
INDEXES={
    'admin_audit_logs':[
        IndexModel([('created_at',1)],name='ttl_admin_audit_180d',expireAfterSeconds=RETENTION_SECONDS),
        IndexModel([('actor_id',1),('request_id',1)],name='ix_admin_audit_actor_request'),
        IndexModel([('resource_type',1),('resource_id',1),('created_at',-1)],name='ix_admin_audit_resource'),
    ],
    'admin_write_requests':[
        IndexModel([('actor_id',1),('request_id',1)],name='uq_admin_write_actor_request',unique=True),
        IndexModel([('expires_at',1)],name='ttl_admin_write_expiry',expireAfterSeconds=0),
    ],
}
