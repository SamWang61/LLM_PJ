"""Real local MongoDB validation and transaction checks; never uses Atlas/.env."""
from datetime import datetime,timedelta,timezone
import os
from uuid import uuid4
import pytest
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError,WriteError
import migrate_admin_audit as migration
from schema_d5_v1 import RETENTION_SECONDS


@pytest.fixture
def db():
    uri=os.environ.get('D5_TEST_MONGO_URI')
    if not uri: pytest.skip('D5_TEST_MONGO_URI absent; local replica set required')
    name='sam_d5_acceptance_'+uuid4().hex
    migration.local_target(uri,name)
    client=MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=5000)
    assert client.admin.command('hello').get('setName')
    try: yield client[name]
    finally:
        client.drop_database(name)
        client.close()


def audit(**extra):
    return {'_id':ObjectId(),'schema_version':4,'actor_id':ObjectId(),'request_id':str(uuid4()),
        'resource_type':'product','resource_id':ObjectId(),'before':{'status':'active'},
        'after':{'status':'inactive'},'reason':'local D5 acceptance','result':'succeeded',
        'created_at':datetime.now(timezone.utc),**extra}


def receipt(**extra):
    now=datetime.now(timezone.utc)
    return {'_id':ObjectId(),'schema_version':4,'actor_id':ObjectId(),'request_id':str(uuid4()),
        'request_hash':'a'*64,'mode':'single','result':{'status':'succeeded','http_status':200,'items':[]},
        'created_at':now,'expires_at':now+timedelta(seconds=RETENTION_SECONDS),**extra}


def test_preflight_is_read_only_and_apply_replays_one_ledger(db):
    assert migration.preflight(db)['written'] is False
    assert db.list_collection_names()==[]
    assert migration.apply(db)['indexes']==7
    assert migration.apply(db)['status']=='succeeded'
    assert db.schema_migrations.count_documents({'_id':migration.MIGRATION})==1
    assert db.schema_migrations.find_one()['checksum']==migration.checksum()


@pytest.mark.parametrize('document',[
    audit(after={'status':'inactive','password_hash':'forbidden'}),
    audit(resource_type='customer',before={'role':'customer'},after={'role':'admin'}),
    audit(request_id=str(uuid4())+':100'),
    receipt(result={'status':'succeeded','http_status':200,'items':[],'token':'forbidden'}),
    receipt(expires_at=datetime.now(timezone.utc)+timedelta(days=179)),
])
def test_validator_rejects_secret_or_out_of_contract_fields(db,document):
    migration.apply(db)
    collection=db.admin_audit_logs if 'resource_type' in document else db.admin_write_requests
    with pytest.raises(WriteError) as failed:
        collection.insert_one(document)
    assert failed.value.code==121
    assert collection.count_documents({})==0


def test_receipt_uniqueness_is_actor_scoped_and_batch_item_id_is_accepted(db):
    migration.apply(db)
    first=receipt();db.admin_write_requests.insert_one(first)
    with pytest.raises(DuplicateKeyError):
        db.admin_write_requests.insert_one({**first,'_id':ObjectId()})
    db.admin_write_requests.insert_one({**first,'_id':ObjectId(),'actor_id':ObjectId()})
    db.admin_write_requests.insert_one({**first,'_id':ObjectId(),'request_id':first['request_id']+':99','mode':'per_item'})
    assert db.admin_write_requests.count_documents({})==3
    indexes={i['name']:i for i in db.admin_write_requests.list_indexes()}
    assert indexes['ttl_admin_write_expiry']['expireAfterSeconds']==0
    audit_indexes={i['name']:i for i in db.admin_audit_logs.list_indexes()}
    assert audit_indexes['ttl_admin_audit_180d']['expireAfterSeconds']==RETENTION_SECONDS


def test_business_audit_and_receipt_commit_together(db):
    migration.apply(db)
    resource=ObjectId();db.d5_probe_resources.insert_one({'_id':resource,'status':'active'})
    event=audit(resource_id=resource)
    with db.client.start_session() as session:
        with session.start_transaction():
            db.d5_probe_resources.update_one({'_id':resource},{'$set':{'status':'inactive'}},session=session)
            db.admin_audit_logs.insert_one(event,session=session)
            db.admin_write_requests.insert_one(receipt(actor_id=event['actor_id'],request_id=event['request_id']),session=session)
    assert db.d5_probe_resources.find_one()['status']=='inactive'
    assert db.admin_audit_logs.count_documents({})==db.admin_write_requests.count_documents({})==1


def test_invalid_audit_rolls_back_business_update(db):
    migration.apply(db)
    resource=ObjectId();db.d5_probe_resources.insert_one({'_id':resource,'status':'active'})
    with pytest.raises(WriteError):
        with db.client.start_session() as session:
            with session.start_transaction():
                db.d5_probe_resources.update_one({'_id':resource},{'$set':{'status':'inactive'}},session=session)
                db.admin_audit_logs.insert_one(audit(resource_id=resource,after={'password_hash':'forbidden'}),session=session)
    assert db.d5_probe_resources.find_one()['status']=='active'
    assert db.admin_audit_logs.count_documents({})==db.admin_write_requests.count_documents({})==0


def test_duplicate_receipt_rolls_back_business_and_audit(db):
    migration.apply(db)
    request=receipt();db.admin_write_requests.insert_one(request)
    resource=ObjectId();db.d5_probe_resources.insert_one({'_id':resource,'status':'active'})
    with pytest.raises(DuplicateKeyError):
        with db.client.start_session() as session:
            with session.start_transaction():
                db.d5_probe_resources.update_one({'_id':resource},{'$set':{'status':'inactive'}},session=session)
                db.admin_audit_logs.insert_one(audit(resource_id=resource),session=session)
                db.admin_write_requests.insert_one({**request,'_id':ObjectId()},session=session)
    assert db.d5_probe_resources.find_one()['status']=='active'
    assert db.admin_audit_logs.count_documents({})==0
    assert db.admin_write_requests.count_documents({})==1


def test_validator_drift_refused_before_creating_other_collection(db):
    db.create_collection('admin_audit_logs',validator={'$jsonSchema':{'bsonType':'object'}},validationLevel='strict',validationAction='error')
    before=set(db.list_collection_names())
    with pytest.raises(ValueError,match='validator drift'):
        migration.apply(db)
    assert set(db.list_collection_names())==before
    assert 'admin_write_requests' not in before


def test_existing_active_contract_is_not_implicitly_upgraded():
    from schema_active_v4 import SCHEMAS,MIGRATIONS
    from admin_session_audit_schema import SCHEMAS as SESSION_SCHEMAS, MIGRATION as SESSION_MIGRATION
    assert all(SCHEMAS[name] == validator for name, validator in SESSION_SCHEMAS.items())
    assert SESSION_MIGRATION in MIGRATIONS
    assert migration.MIGRATION not in MIGRATIONS


@pytest.mark.parametrize('uri,name',[
    ('mongodb+srv://unused@example.invalid/vibecart_ai','vibecart_ai'),
    ('mongodb://user:pass@localhost/','sam_d5_acceptance_test'),
    ('mongodb://localhost/','vibecart_ai'),
])
def test_cli_refuses_production_or_credentialed_targets(uri,name):
    with pytest.raises(ValueError): migration.local_target(uri,name)
