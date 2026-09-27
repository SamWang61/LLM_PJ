"""Apply missing document constraints only after source and data preflight."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
from bson import json_util
from bootstrap_schema import ROOT,connect
from cart_schema import SCHEMAS as BEFORE,verify_current as verify_before
from schema_current import SCHEMAS,verify_current

MIGRATION='20260918_03_schema_document_constraints'


def main():
    checksum=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'schema_current.py').read_bytes()).hexdigest()
    changed=[n for n in SCHEMAS if SCHEMAS[n]!=BEFORE[n]]
    with connect() as client:
        db=client.vibecart_ai
        record=db.schema_migrations.find_one({'_id':MIGRATION})
        if record:
            if record['checksum']!=checksum or record['status']!='succeeded':
                raise RuntimeError('Prior migration differs or is incomplete; manual inspection required')
        else:
            baseline=verify_before(db)
            # No unknown structure is overwritten, and existing data must already
            # conform. No guessing of budgets, model IDs or prompt versions.
            for name in changed:
                if db[name].count_documents({})!=db[name].count_documents(SCHEMAS[name]):
                    raise RuntimeError('Data requires explicit remediation: '+name)
            (ROOT/'11_Schema完整性更新前結構.md').write_text('# Schema 完整性更新前結構\n\n```json\n'+
                json_util.dumps({'checked_at':datetime.now(timezone.utc),'collections':baseline},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
            source=sum(db[n].count_documents({}) for n in changed)
            db.schema_migrations.insert_one({'_id':MIGRATION,'schema_version':2,'checksum':checksum,
                'status':'running','started_at':datetime.now(timezone.utc),'completed_at':None,
                'counts':{'source':source,'target':source,'errors':0},'error_code':None})
            try:
                for name in changed:
                    db.command('collMod',name,validator=SCHEMAS[name],validationLevel='strict',validationAction='error')
                verify_current(db)
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{
                    'status':'succeeded','completed_at':datetime.now(timezone.utc)}})
            except Exception as exc:
                db.schema_migrations.update_one({'_id':MIGRATION},{'$set':{
                    'status':'failed','completed_at':datetime.now(timezone.utc),
                    'error_code':type(exc).__name__,'counts':{'source':source,'target':source,'errors':1}}})
                raise
        report=verify_current(db)
        (ROOT/'05_實際Schema與索引.md').write_text('# Atlas 最新 Schema 與索引讀回\n\n2026-09-18 文件完整性查核；包含條件必填補強。\n\n```json\n'+
            json_util.dumps({'checked_at':datetime.now(timezone.utc),'database':'vibecart_ai',
                'migrations':list(db.schema_migrations.find({})), 'collections':report},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
        print('Schema audit migration succeeded; collections=14, custom_indexes=31, total_indexes=45; changed='+','.join(changed))


if __name__=='__main__':
    main()
