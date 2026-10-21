"""Scoped production contract for audited customer-device revocation.

The broader D5 draft remains immutable and is not activated by this migration.
"""
from pymongo import IndexModel

MIGRATION = '20261021_08_customer_session_audit_v4'
RETENTION_SECONDS = 180 * 86400


def obj(properties):
    return {'bsonType': 'object', 'required': list(properties),
            'additionalProperties': False, 'properties': properties}


OID = {'bsonType': 'objectId'}
DATE = {'bsonType': 'date'}
COUNT = {'bsonType': 'int', 'minimum': 0}
VERSION = {'bsonType': 'int', 'enum': [4]}
REQUEST_ID = {'bsonType': 'string', 'pattern':
              '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'}
AUDIT = {'$jsonSchema': obj({
    '_id': OID, 'schema_version': VERSION, 'actor_id': OID, 'request_id': REQUEST_ID,
    'resource_type': {'enum': ['customer_sessions']}, 'resource_id': OID,
    'before': obj({'device_count': COUNT}),
    'after': obj({'device_count': {'bsonType': 'int', 'enum': [0]}}),
    'reason': {'bsonType': 'string', 'minLength': 1, 'maxLength': 500},
    'result': {'enum': ['succeeded']}, 'created_at': DATE,
})}
RECEIPT = {'$jsonSchema': obj({
    '_id': OID, 'schema_version': VERSION, 'actor_id': OID, 'request_id': REQUEST_ID,
    'request_hash': {'bsonType': 'string', 'pattern': '^[a-f0-9]{64}$'},
    'mode': {'enum': ['single']},
    'result': obj({'status': {'enum': ['succeeded']},
                   'http_status': {'bsonType': 'int', 'enum': [302]}, 'revoked_count': COUNT}),
    'created_at': DATE, 'expires_at': DATE,
}), '$expr': {'$eq': ['$expires_at', {'$add': ['$created_at', RETENTION_SECONDS * 1000]}]}}
SCHEMAS = {'admin_audit_logs': AUDIT, 'admin_write_requests': RECEIPT}
INDEXES = {
    'admin_audit_logs': [
        IndexModel([('created_at', 1)], name='ttl_admin_audit_180d', expireAfterSeconds=RETENTION_SECONDS),
        IndexModel([('actor_id', 1), ('request_id', 1)], name='ix_admin_audit_actor_request'),
        IndexModel([('resource_type', 1), ('resource_id', 1), ('created_at', -1)], name='ix_admin_audit_resource'),
    ],
    'admin_write_requests': [
        IndexModel([('actor_id', 1), ('request_id', 1)], name='uq_admin_write_actor_request', unique=True),
        IndexModel([('expires_at', 1)], name='ttl_admin_write_expiry', expireAfterSeconds=0),
    ],
}
