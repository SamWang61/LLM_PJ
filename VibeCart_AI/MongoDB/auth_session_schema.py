"""Additive device-session schema. No existing collection is changed."""
from pymongo import IndexModel

MIGRATION = '20261014_06_member_device_sessions_v4'
VALIDATOR = {'$jsonSchema': {'bsonType': 'object', 'additionalProperties': False,
    'required': ['_id', 'schema_version', 'user_id', 'auth_fingerprint', 'created_at', 'expires_at'],
    'properties': {'_id': {'bsonType': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'schema_version': {'bsonType': 'int', 'enum': [4]}, 'user_id': {'bsonType': 'objectId'},
        'auth_fingerprint': {'bsonType': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'created_at': {'bsonType': 'date'}, 'expires_at': {'bsonType': 'date'}}}}
INDEXES = [IndexModel([('user_id', 1)], name='ix_auth_sessions_user'),
           IndexModel([('expires_at', 1)], name='ttl_auth_sessions_expiry', expireAfterSeconds=0)]
