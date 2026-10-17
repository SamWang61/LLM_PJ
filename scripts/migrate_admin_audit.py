"""D5 additive migration, currently restricted to disposable localhost rehearsal.

Preflight never writes. Explicit --apply is required; Atlas is refused until the
active checker and production rollout have been separately reviewed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from pymongo import MongoClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'VibeCart_AI/MongoDB'))
from schema_d5_v1 import MIGRATION,SCHEMAS,INDEXES


def checksum():
    return hashlib.sha256((ROOT/'VibeCart_AI/MongoDB/schema_d5_v1.py').read_bytes()
                          +Path(__file__).read_bytes()).hexdigest()


def preflight(db):
    existing=set(db.list_collection_names())
    for name,validator in SCHEMAS.items():
        if name not in existing: continue
        options=db[name].options()
        if (options.get('validator')!=validator or options.get('validationLevel')!='strict'
                or options.get('validationAction')!='error'):
            raise ValueError('Existing D5 validator drift; no automatic replacement')
        actual={index['name']:index for index in db[name].list_indexes()}
        wanted={model.document['name']:model.document for model in INDEXES[name]}
        if set(actual)-{'_id_'}-set(wanted):
            raise ValueError('Unexpected existing D5 index')
        for key,index in wanted.items():
            if key not in actual: continue
            found=actual[key]
            if (list(found['key'].items())!=list(index['key'].items())
                    or bool(found.get('unique'))!=bool(index.get('unique'))
                    or found.get('expireAfterSeconds')!=index.get('expireAfterSeconds')):
                raise ValueError('Existing D5 index drift; no automatic replacement')
            if any(found.get(option)!=index.get(option) for option in ('partialFilterExpression','sparse','collation','hidden')):
                raise ValueError('Unexpected D5 index constraint')
    record=db.schema_migrations.find_one({'_id':MIGRATION})
    if record and (record.get('status')!='succeeded' or record.get('checksum')!=checksum()):
        raise ValueError('Changed or incomplete D5 migration')
    if record and not set(SCHEMAS)<=existing:
        raise ValueError('Recorded D5 collection missing; repair requires explicit recovery')
    return {'migration':MIGRATION,'status':'preflight-passed','existing':len(existing&set(SCHEMAS)),
            'planned_collections':2,'written':False,'active_contract_changed':False}


def apply(db):
    preflight(db)  # Check both targets before any DDL; partial failures are resumable.
    existing=set(db.list_collection_names())
    for name,validator in SCHEMAS.items():
        if name not in existing:
            db.create_collection(name,validator=validator,validationLevel='strict',validationAction='error')
        db[name].create_indexes(INDEXES[name])
    preflight(db)
    now=datetime.now(timezone.utc)
    db.schema_migrations.update_one({'_id':MIGRATION},{'$setOnInsert':{
        'schema_version':2,'checksum':checksum(),'status':'succeeded','started_at':now,
        'completed_at':now,'counts':{'source':0,'target':0,'errors':0},'error_code':None}},upsert=True)
    return {'migration':MIGRATION,'status':'succeeded','written':True,
            'collections':2,'indexes':sum(len(list(db[n].list_indexes())) for n in SCHEMAS),
            'active_contract_changed':False}


def local_target(uri,name):
    parsed=urlsplit(uri)
    if (parsed.scheme!='mongodb' or parsed.hostname not in {'localhost','127.0.0.1'}
            or parsed.username or parsed.password or ',' in parsed.netloc
            or parsed.path not in {'','/'} or not name.startswith('sam_d5_acceptance_')):
        raise ValueError('Only a disposable credential-free localhost D5 database is admitted')
    return uri,name


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uri',required=True);parser.add_argument('--database',required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    uri,name=local_target(args.uri,args.database)
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=5000) as client:
        if not client.admin.command('hello').get('setName'):
            raise ValueError('Replica set required')
        print(json.dumps((apply if args.apply else preflight)(client[name])))


if __name__=='__main__':
    main()
