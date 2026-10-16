"""Explicit additive migration; never run during web startup."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from pymongo import MongoClient
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'VibeCart_AI/MongoDB'))
from auth_session_schema import MIGRATION, VALIDATOR, INDEXES


def apply(db):
    checksum = hashlib.sha256((ROOT/'VibeCart_AI/MongoDB/auth_session_schema.py').read_bytes()+Path(__file__).read_bytes()).hexdigest()
    record = db.schema_migrations.find_one({'_id': MIGRATION})
    if record and (record['checksum'] != checksum or record['status'] != 'succeeded'):
        raise RuntimeError('Changed or incomplete session migration')
    if 'auth_sessions' not in db.list_collection_names():
        db.create_collection('auth_sessions', validator=VALIDATOR, validationLevel='strict', validationAction='error')
    elif db.auth_sessions.options().get('validator') != VALIDATOR:
        raise RuntimeError('Unexpected existing auth_sessions validator')
    db.auth_sessions.create_indexes(INDEXES)
    if not record:
        now = datetime.now(timezone.utc)
        db.schema_migrations.insert_one({'_id': MIGRATION, 'schema_version': 2, 'checksum': checksum,
            'status': 'succeeded', 'started_at': now, 'completed_at': now,
            'counts': {'source': 0, 'target': 0, 'errors': 0}, 'error_code': None})
    return {'migration': MIGRATION, 'status': 'succeeded', 'indexes': len(list(db.auth_sessions.list_indexes())),
            'existing_users_unchanged': True, 'collections': len(db.list_collection_names())}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply', action='store_true');args=parser.parse_args()
    if not args.apply: raise SystemExit('Explicit --apply required')
    uri=os.environ.get('MONGO_URI','')
    if urlparse(uri).hostname != 'vibecart-ai-free.odqe25w.mongodb.net':
        raise SystemExit('Unauthorized database target')
    with MongoClient(uri, serverSelectionTimeoutMS=10000) as client:
        print(json.dumps(apply(client.vibecart_ai)))
