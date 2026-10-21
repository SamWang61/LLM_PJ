"""Add customer-session audit/receipts; default is a read-only preflight.

Production apply requires an explicit database confirmation. Existing validators,
indexes, migration checksums and business records are never replaced.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'VibeCart_AI/MongoDB'))
from admin_session_audit_schema import MIGRATION, SCHEMAS, INDEXES


def checksum():
    return hashlib.sha256((ROOT / 'VibeCart_AI/MongoDB/admin_session_audit_schema.py').read_bytes()
                          + Path(__file__).read_bytes()).hexdigest()


def preflight(db):
    existing = set(db.list_collection_names())
    record = db.schema_migrations.find_one({'_id': MIGRATION})
    if record and (record.get('status') != 'succeeded' or record.get('checksum') != checksum()):
        raise ValueError('Changed or incomplete session-audit migration')
    if record and not set(SCHEMAS) <= existing:
        raise ValueError('Recorded audit collection missing; explicit recovery required')
    for name, validator in SCHEMAS.items():
        if name not in existing:
            continue
        options = db[name].options()
        if (options.get('validator') != validator or options.get('validationLevel') != 'strict'
                or options.get('validationAction') != 'error'):
            raise ValueError('Existing audit validator drift; no automatic replacement')
        if db[name].count_documents({'$nor': [validator]}, limit=1):
            raise ValueError('Existing audit document violates the contract')
        actual = {index['name']: index for index in db[name].list_indexes()}
        wanted = {model.document['name']: model.document for model in INDEXES[name]}
        if set(actual) - {'_id_'} - set(wanted) or (record and set(wanted) - set(actual)):
            raise ValueError('Unexpected or missing audit index')
        for key, index in wanted.items():
            if key not in actual:
                continue
            found = actual[key]
            if (list(found['key'].items()) != list(index['key'].items())
                    or bool(found.get('unique')) != bool(index.get('unique'))
                    or found.get('expireAfterSeconds') != index.get('expireAfterSeconds')
                    or any(found.get(option) != index.get(option) for option in
                           ('partialFilterExpression', 'sparse', 'collation', 'hidden'))):
                raise ValueError('Existing audit index drift; no automatic replacement')
    return {'migration': MIGRATION, 'status': 'preflight-passed',
            'existing': len(existing & set(SCHEMAS)), 'written': False}


def apply(db):
    preflight(db)  # Inspect both targets before any DDL; a partial DDL run is resumable.
    existing = set(db.list_collection_names())
    for name, validator in SCHEMAS.items():
        if name not in existing:
            db.create_collection(name, validator=validator, validationLevel='strict', validationAction='error')
        db[name].create_indexes(INDEXES[name])
    preflight(db)
    now = datetime.now(timezone.utc)
    db.schema_migrations.update_one({'_id': MIGRATION}, {'$setOnInsert': {
        'schema_version': 2, 'checksum': checksum(), 'status': 'succeeded', 'started_at': now,
        'completed_at': now, 'counts': {'source': 0, 'target': 0, 'errors': 0}, 'error_code': None}}, upsert=True)
    preflight(db)
    return {'migration': MIGRATION, 'status': 'succeeded', 'collections': 2,
            'indexes': sum(len(list(db[n].list_indexes())) for n in SCHEMAS)}


def target(uri, name):
    parsed = urlsplit(uri)
    local = (parsed.scheme == 'mongodb' and parsed.hostname in {'127.0.0.1', 'localhost'}
             and not parsed.username and not parsed.password and ',' not in parsed.netloc
             and parsed.path in {'', '/'} and name.startswith(('ren_acceptance_', 'sam_d5_acceptance_')))
    production = (parsed.scheme == 'mongodb+srv' and parsed.hostname == 'vibecart-ai-free.odqe25w.mongodb.net'
                  and name == 'vibecart_ai' and parsed.path in {'', '/', '/vibecart_ai'})
    if not (local or production):
        raise ValueError('Target is outside the reviewed session-audit rollout')
    return uri, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database-confirm')
    args = parser.parse_args()
    uri, name = target(os.environ['MONGO_URI'], os.environ['MONGO_DB'])
    if args.apply and args.database_confirm != name:
        raise ValueError('Explicit database confirmation is required')
    with MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000) as client:
        if not client.admin.command('hello').get('setName'):
            raise ValueError('Replica set required')
        print(json.dumps((apply if args.apply else preflight)(client[name])))


if __name__ == '__main__':
    main()
