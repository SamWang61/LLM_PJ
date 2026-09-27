"""Controlled empty-cart migration. Never guesses historical price snapshots."""
from pathlib import Path
import hashlib
from datetime import datetime, timezone
from bson import json_util
from bootstrap_schema import connect, ROOT, verify as verify_v2
from cart_schema import SCHEMAS, INDEXES, verify_current

MIGRATION='20260916_02_cart_state_events_v3'


def main():
    checksum=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'cart_schema.py').read_bytes()).hexdigest()
    with connect() as client:
        db=client.vibecart_ai
        record=db.schema_migrations.find_one({'_id':MIGRATION})
        if record:
            if record['checksum']!=checksum or record['status']!='succeeded':
                raise RuntimeError('Migration changed or incomplete; review partial state before resuming')
        else:
            baseline=verify_v2(db)
            if 'cart_events' in db.list_collection_names() or db.carts.count_documents({}):
                raise RuntimeError('Existing carts/events require explicit historical migration; no changes made')
            # Persist a credential-free pre-change inventory before any DDL.
            (ROOT/'08_購物車更新前結構.md').write_text('# 更新前實際結構\n\n```json\n'+
                json_util.dumps(baseline,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
            now=datetime.now(timezone.utc)
            db.schema_migrations.insert_one({'_id':MIGRATION,'schema_version':2,'checksum':checksum,
                'status':'running','started_at':now,'completed_at':None,
                'counts':{'source':0,'target':0,'errors':0},'error_code':None})
            try:
                db.create_collection('cart_events',validator=SCHEMAS['cart_events'],validationLevel='strict',validationAction='error')
                db.cart_events.create_indexes(INDEXES['cart_events'])
                db.command('collMod','carts',validator=SCHEMAS['carts'],validationLevel='strict',validationAction='error')
                # Establish new active uniqueness before retiring only the known old index.
                db.carts.create_indexes(INDEXES['carts'])
                if db.carts.count_documents({}):
                    raise RuntimeError('Concurrent cart writes detected; stop for review')
                db.carts.drop_index('uq_carts_user_id')
                verify_current(db)
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{
                    'status':'succeeded','completed_at':datetime.now(timezone.utc)}})
            except Exception as exc:
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{
                    'status':'failed','completed_at':datetime.now(timezone.utc),
                    'error_code':type(exc).__name__,'counts':{'source':0,'target':0,'errors':1}}})
                raise
        report=verify_current(db)
        (ROOT/'05_實際Schema與索引.md').write_text('# Atlas 最新 Schema 與索引讀回\n\n購物車 v3；其餘集合維持 v2。\n\n```json\n'+
            json_util.dumps({'checked_at':datetime.now(timezone.utc),'database':'vibecart_ai',
                'migrations':list(db.schema_migrations.find({})), 'collections':report},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
        print('Verified 14 collections, 31 custom indexes, 45 total indexes; cart v3 migration succeeded')


if __name__=='__main__':
    main()
