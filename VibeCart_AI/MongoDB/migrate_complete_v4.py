"""Migrate verified empty redesigned collections, retaining all AI/technical data."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
from bson import json_util
from bootstrap_schema import ROOT,connect
from schema_current import verify_current as verify_before,SCHEMAS as BEFORE
from schema_complete_v4 import SCHEMAS,INDEXES,CORE,CHANGED,default_policy,verify_complete

MIGRATION='20260918_04_complete_catalog_schema_v4'
SOURCE=ROOT/'13_完整Schema_v1.0_來源快照.md'


def main():
    checksum=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'schema_complete_v4.py').read_bytes()+SOURCE.read_bytes()).hexdigest()
    with connect() as client:
        db=client.vibecart_ai
        record=db.schema_migrations.find_one({'_id':MIGRATION})
        if record:
            if record['status']!='succeeded' or record['checksum']!=checksum:
                raise RuntimeError('Changed or partially applied migration; inspect before resuming')
        else:
            baseline=verify_before(db)
            if set(db.list_collection_names())!=set(BEFORE):
                raise RuntimeError('Unknown collections; inspect before writing')
            if any(db[n].count_documents({}) for n in CHANGED):
                raise RuntimeError('Redesigned collections have data; explicit data migration required')
            (ROOT/'14_完整Schema更新前結構.md').write_text('# 完整 Schema 更新前結構\n\n```json\n'+
                json_util.dumps({'checked_at':datetime.now(timezone.utc),'collections':baseline},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
            db.schema_migrations.insert_one({'_id':MIGRATION,'schema_version':2,'checksum':checksum,'status':'running',
                'started_at':datetime.now(timezone.utc),'completed_at':None,
                'counts':{'source':0,'target':0,'errors':0},'error_code':None})
            try:
                for name in CORE:
                    if name in BEFORE:
                        db.command('collMod',name,validator=SCHEMAS[name],validationLevel='strict',validationAction='error')
                    else:
                        db.create_collection(name,validator=SCHEMAS[name],validationLevel='strict',validationAction='error')
                    desired={i.document['name'] for i in INDEXES[name]}
                    # Establish desired constraints before retiring verified obsolete indexes.
                    if INDEXES[name]: db[name].create_indexes(INDEXES[name])
                    if name in BEFORE:
                        if db[name].count_documents({}):
                            raise RuntimeError('Concurrent writes detected: '+name)
                        old=next(r for r in baseline if r['collection']==name)['indexes']
                        for index in old:
                            if index['name']!='_id_' and index['name'] not in desired:
                                db[name].drop_index(index['name'])
                db.system_configs.insert_one(default_policy())
                verify_complete(db)
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{'status':'succeeded',
                    'completed_at':datetime.now(timezone.utc),'counts':{'source':0,'target':1,'errors':0}}})
            except Exception as exc:
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{'status':'failed',
                    'completed_at':datetime.now(timezone.utc),'error_code':type(exc).__name__,
                    'counts':{'source':0,'target':0,'errors':1}}})
                raise
        report=verify_complete(db)
        total=sum(len(r['indexes']) for r in report)
        (ROOT/'05_實際Schema與索引.md').write_text('# Atlas 最新完整 Schema 讀回\n\n核心 19 集合 v4；保留既有 8 集合。\n\n```json\n'+
            json_util.dumps({'checked_at':datetime.now(timezone.utc),'database':'vibecart_ai',
                'migrations':list(db.schema_migrations.find({})),'collections':report},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
        print(f'Complete schema v4 verified: {len(report)} collections, {total-len(report)} custom indexes, {total} total indexes')


if __name__=='__main__': main()
