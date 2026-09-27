"""Live positive/negative schema checks for every collection. All writes abort."""
import math
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from bson import ObjectId, Decimal128
from pymongo.errors import OperationFailure
from bootstrap_schema import connect
from schema_current import SCHEMAS, verify_current


def value(schema, field=''):
    if 'enum' in schema:
        return None if None in schema['enum'] else schema['enum'][0]
    t=schema.get('bsonType')
    if isinstance(t,list):
        if 'null' in t:
            return None
        t=t[0]
    if t=='object':
        return {key:value(spec,key) for key,spec in schema.get('properties',{}).items()}
    if t=='array':
        return [value(schema['items'],field) for _ in range(schema.get('minItems',0))]
    if t=='objectId': return ObjectId()
    if t=='date': return datetime.now(timezone.utc)
    if t=='bool': return False
    if t=='null': return None
    if t=='int': return int(schema.get('minimum',0))
    if t=='double': return 0.5
    if t=='decimal': return Decimal128('0.00')
    if t=='string':
        if field in ('checksum','content_hash','request_hash'): return '0'*64
        if field=='event_type': return 'VIEW'
        if field=='sku': return 'SCHEMA-TEST-'+uuid4().hex.upper()
        if field in ('_id','event_id','operation_id','email','slug','name','order_number','checkout_id'):
            return 'schema-test-'+uuid4().hex
        return 'x'*max(schema.get('minLength',1),1)
    raise RuntimeError('No example generator for '+repr(schema))


def example(name):
    document=value(SCHEMAS[name]['$jsonSchema'])
    if name=='user_events':
        document['product_id']=ObjectId()
    if name=='ai_insights':
        document['period_end']=document['period_start']+timedelta(days=1)
    return document


@pytest.fixture(scope='module')
def db():
    with connect('.env') as client:
        db=client.vibecart_ai
        before={n:db[n].count_documents({}) for n in SCHEMAS}
        yield db
        after={n:db[n].count_documents({}) for n in SCHEMAS}
        assert before==after, 'Test documents were not fully rolled back'


def insert_check(db,name,document,expected=None):
    with db.client.start_session() as session:
        session.start_transaction()
        try:
            if expected is None:
                db[name].insert_one(document,session=session)
            else:
                with pytest.raises(OperationFailure) as exc:
                    db[name].insert_one(document,session=session)
                assert exc.value.code==expected
        finally:
            if session.in_transaction:
                session.abort_transaction()


@pytest.mark.parametrize('name',list(SCHEMAS))
def test_all_collections_accept_valid_document(db,name):
    insert_check(db,name,example(name))


@pytest.mark.parametrize('name',list(SCHEMAS))
def test_all_collections_reject_missing_schema_version(db,name):
    document=example(name)
    del document['schema_version']
    insert_check(db,name,document,121)


@pytest.mark.parametrize('bad',[Decimal128('1.234'),Decimal128('Infinity'),Decimal128('NaN'),0.1,-1])
def test_budget_precision_type_and_finiteness(db,bad):
    document=value(SCHEMAS['users']['$jsonSchema'])
    document['preferences']['budget_min']=bad
    insert_check(db,'users',document,121)


def model_request():
    document=value(SCHEMAS['ai_requests']['$jsonSchema'])
    now=datetime.now(timezone.utc)
    document.update(task_type='sales_summary',status='succeeded',is_success=True,
        execution_mode='api',actual_provider='anthropic',requested_provider='anthropic',
        model_name='test-model',model_revision='test-revision',prompt_name='sales',prompt_version='v1',
        started_at=now,completed_at=now,latency_ms=1)
    return document


@pytest.mark.parametrize('field',['model_name','model_revision','prompt_name','prompt_version','started_at','completed_at','latency_ms','actual_provider'])
def test_ai_success_required_provenance(db,field):
    document=model_request()
    document[field]=None
    insert_check(db,'ai_requests',document,121)


def test_valid_model_and_pre_execution_failure(db):
    insert_check(db,'ai_requests',model_request())
    document=value(SCHEMAS['ai_requests']['$jsonSchema'])
    document.update(status='failed',is_success=False,latency_ms=0,completed_at=datetime.now(timezone.utc))
    insert_check(db,'ai_requests',document)


def test_running_requires_start_date(db):
    document=value(SCHEMAS['ai_requests']['$jsonSchema'])
    document.update(status='running')
    insert_check(db,'ai_requests',document,121)


@pytest.mark.parametrize('bad',[Decimal128('Infinity'),Decimal128('NaN'),Decimal128('-1')])
def test_cost_finite_nonnegative(db,bad):
    document=value(SCHEMAS['ai_requests']['$jsonSchema'])
    document.update(estimated_cost=bad,cost_currency='USD')
    insert_check(db,'ai_requests',document,121)


def test_small_fractional_cost_is_preserved(db):
    document=model_request()
    document.update(estimated_cost=Decimal128('0.000001'),cost_currency='USD')
    insert_check(db,'ai_requests',document)


def test_recommendation_click_requires_product(db):
    document=value(SCHEMAS['user_events']['$jsonSchema'])
    document.update(event_type='recommendation_click',recommendation_id=ObjectId(),product_id=None)
    insert_check(db,'user_events',document,121)
    document['product_id']=ObjectId()
    insert_check(db,'user_events',document)


@pytest.mark.parametrize('field',['model','revision'])
def test_bge_provenance_not_blank(db,field):
    document=value(SCHEMAS['recommendations']['$jsonSchema'])
    document.update(strategy='bge_personalized',model='BAAI/bge-small-zh-v1.5',revision='fixed')
    document[field]=''
    insert_check(db,'recommendations',document,121)


def test_current_settings_and_existing_data():
    with connect() as client:
        report=verify_current(client.vibecart_ai)
        assert len(report)==14
        assert sum(len(r['indexes']) for r in report)==45
        assert sum(i.get('unique',False) for r in report for i in r['indexes'] if i['name']!='_id_')==12
        ttl=[(r['collection'],i['expireAfterSeconds']) for r in report for i in r['indexes'] if 'expireAfterSeconds' in i]
        assert sorted(ttl)==[('ai_insights',0),('request_limits',0)]
