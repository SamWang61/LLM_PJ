"""Live tests for complete catalog schema and SKU transaction services."""
import sys
from pathlib import Path
from uuid import uuid4
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from bson import ObjectId,Decimal128
from pymongo.errors import OperationFailure
from bootstrap_schema import connect
from schema_complete_v4 import SCHEMAS,CORE,verify_complete,default_policy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.sku_cart_service import CartService,CartError,CartConflict
from services.review_service import ReviewService


def sample_value(schema,field=''):
    if 'enum' in schema: return None if None in schema['enum'] else schema['enum'][0]
    t=schema.get('bsonType')
    if isinstance(t,list):
        if 'null' in t: return None
        t=t[0]
    if t=='object': return {k:sample_value(v,k) for k,v in schema.get('properties',{}).items()}
    if t=='array': return [sample_value(schema['items']) for _ in range(schema.get('minItems',0))]
    if t=='objectId': return ObjectId()
    if t=='date': return datetime.now(timezone.utc)
    if t=='bool': return False
    if t=='int': return int(schema.get('minimum',0))
    if t=='double': return max(0.5,float(schema.get('minimum',0)))
    if t=='decimal': return Decimal128('0.00')
    if t=='null': return None
    if t=='string':
        if field in ('checksum','content_hash','request_hash'): return '0'*64
        if field=='event_type': return 'VIEW'
        return ('fixture-'+uuid4().hex) if field in ('_id','email','name','slug','sku','sku_code','product_code',
               'category_code','brand_code','event_id','operation_id','order_number','checkout_id','recommendation_id') else 'x'*max(1,schema.get('minLength',1))
    raise RuntimeError('Missing generator: '+str(schema))


def example(name):
    d=sample_value(SCHEMAS[name]['$jsonSchema'])
    if name=='users': d['is_active']=True
    if name=='categories': d['path']=[d['category_code']]
    if name=='products':
        d.update(rating_default_value=4.0,average_rating_display=4.0,average_rating_raw=None)
    if name in ('user_events','behavior_events'): d['product_id']=ObjectId()
    if name=='behavior_events': d.update(user_id=ObjectId(),order_id=ObjectId())
    if name in ('ai_insights','product_repurchase_stats'): d['period_end']=d['period_start']+timedelta(days=1)
    if name=='recommendation_pools': d['expires_at']=d['generated_at']+timedelta(days=1)
    if name=='system_configs': d={'_id':ObjectId(),**default_policy()}
    return d


@pytest.fixture(scope='module')
def db():
    with connect('.env') as c:
        db=c.vibecart_ai
        before={n:db[n].count_documents({}) for n in SCHEMAS}
        yield db
        assert before=={n:db[n].count_documents({}) for n in SCHEMAS}


def check(db,name,d,code=None):
    def write(session):
        if name=='system_configs':
            d.pop('_id',None)
            return db[name].replace_one({'config_key':'recommendation_policy'},d,session=session)
        return db[name].insert_one(d,session=session)
    with db.client.start_session() as s:
        s.start_transaction()
        try:
            if code:
                with pytest.raises(OperationFailure) as error: write(s)
                assert error.value.code==code
            else: write(s)
        finally:
            if s.in_transaction: s.abort_transaction()


@pytest.mark.parametrize('name',list(SCHEMAS))
def test_all_collections_valid(db,name): check(db,name,example(name))


@pytest.mark.parametrize('name',list(SCHEMAS))
def test_all_collections_missing_version(db,name):
    d=example(name);del d['schema_version'];check(db,name,d,121)


def test_score_caps(db):
    for field,score in [('major_categories',70.1),('minor_categories',30.1)]:
        d=example('user_preference_scores')
        d[field]={'category':{'raw_score':100.0,'score':score,'last_event_at':datetime.now(timezone.utc)}}
        check(db,'user_preference_scores',d,121)


@pytest.mark.parametrize('rating',[0,6,4.5])
def test_review_star_range(db,rating):
    d=example('product_reviews');d['rating']=rating;check(db,'product_reviews',d,121)


def test_sku_money_and_available_quantity(db):
    d=example('product_skus');d.update(price=1.0);check(db,'product_skus',d,121)
    d=example('product_skus');d.update(stock_quantity=10,reserved_quantity=2,available_quantity=10)
    check(db,'product_skus',d,121)


def test_rating_default_and_rounding(db):
    d=example('products');d['average_rating_display']=5.0;check(db,'products',d,121)
    d=example('products');d.update(rating_status='ACTUAL',rating_default_value=None,rating_sum=13,rating_count=3,
        rating_distribution={'star_1':0,'star_2':0,'star_3':0,'star_4':2,'star_5':1},
        average_rating_raw=13/3,average_rating_display=4.4)
    check(db,'products',deepcopy(d))
    d['average_rating_display']=4.3;check(db,'products',d,121)


def test_recommendation_counts_and_threshold(db):
    for kind,count in [('PERSONALIZED',7),('CROSS_CATEGORY',5)]:
        d=example('recommendation_logs');d['recommendation_type']=kind
        d['items']=[{'product_id':ObjectId(),'position':i+1,'score':1.0,'reason_code':'TEST'} for i in range(count)]
        check(db,'recommendation_logs',d,121)
    d=example('first_member_recommendations')
    d['items']=[{'major_category_id':ObjectId(),'product_id':ObjectId(),'average_rating_display':4.0,'rating_count':0,'position':1}]
    check(db,'first_member_recommendations',d,121)


@pytest.fixture
def shop(db):
    users=[];products=[];skus=[];categories=[]
    try:
        major=example('categories');db.categories.insert_one(major);categories.append(major['_id'])
        minor=example('categories');minor.update(level=2,parent_id=major['_id'],path=[major['category_code'],minor['category_code']])
        db.categories.insert_one(minor);categories.append(minor['_id'])
        for _ in range(3):
            u=example('users');db.users.insert_one(u);users.append(u['_id'])
        p=example('products');p.update(major_category_id=major['_id'],minor_category_id=minor['_id'],category_path=minor['path'])
        db.products.insert_one(p);products.append(p['_id'])
        for _ in range(2):
            sku=example('product_skus');sku.update(product_id=p['_id'],price=Decimal128('10.00'),
                stock_quantity=20,reserved_quantity=0,available_quantity=20,stock_status='in_stock')
            db.product_skus.insert_one(sku);skus.append(sku['_id'])
        yield CartService(db,enable_checkout=True),users,products,skus
    finally:
        for name in ('product_reviews','order_items','orders','carts','cart_events','behavior_events'):
            db[name].delete_many({'user_id':{'$in':users}})
        db.product_skus.delete_many({'_id':{'$in':skus}})
        db.products.delete_many({'_id':{'$in':products}})
        db.users.delete_many({'_id':{'$in':users}})
        db.categories.delete_many({'_id':{'$in':categories}})


def test_multisku_checkout_and_idempotency(db,shop):
    s,u,p,skus=shop
    c=s.add_item(u[0],skus[0],2,operation_id='a')
    s.add_item(u[0],skus[0],2,operation_id='a')
    c=s.add_item(u[0],skus[1],1,operation_id='b')
    assert len(c['items'])==2
    assert db.behavior_events.count_documents({'user_id':u[0],'event_type':'ADD_TO_CART'})==2
    db.product_skus.update_one({'_id':skus[0]},{'$set':{'price':Decimal128('8.00')}})
    args={'checkout_id':'buy','cart_id':c['_id'],'expected_revision':c['revision']}
    o=s.checkout_cart(u[0],**args)
    assert o['total_amount']==Decimal128('26.00') and 'items' not in o
    assert s.checkout_cart(u[0],**args)['_id']==o['_id']
    assert db.order_items.count_documents({'order_id':o['_id']})==2
    events=list(db.behavior_events.find({'order_id':o['_id'],'event_type':'PURCHASE'}))
    assert len(events)==1 and events[0]['quantity']==3
    assert db.carts.find_one({'_id':c['_id']})['status']=='converted'
    assert s.add_item(u[0],skus[0],1,operation_id='new')['_id']!=c['_id']


def test_checkout_failure_rolls_back(db,shop):
    s,u,p,skus=shop
    s.add_item(u[0],skus[0],1,operation_id='a');c=s.add_item(u[0],skus[1],1,operation_id='b')
    db.product_skus.update_one({'_id':skus[1]},{'$set':{'stock_quantity':0,'available_quantity':0,'stock_status':'out_of_stock'}})
    with pytest.raises(CartError): s.checkout_cart(u[0],checkout_id='buy',cart_id=c['_id'],expected_revision=c['revision'])
    assert db.product_skus.find_one({'_id':skus[0]})['available_quantity']==20
    assert db.orders.count_documents({'user_id':u[0]})==db.order_items.count_documents({'user_id':u[0]})==0
    assert s.get_active_cart(u[0])['revision']==c['revision']


def test_concurrent_last_sku(db,shop):
    s,u,p,skus=shop
    db.product_skus.update_one({'_id':skus[0]},{'$set':{'stock_quantity':1,'available_quantity':1}})
    carts=[s.add_item(uid,skus[0],1,operation_id='add') for uid in u[:2]]
    def buy(i):
        try: return s.checkout_cart(u[i],checkout_id='buy',cart_id=carts[i]['_id'],expected_revision=carts[i]['revision'])
        except CartError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(buy,range(2)))
    assert sum(r is not None for r in results)==1
    assert db.product_skus.find_one({'_id':skus[0]})['available_quantity']==0


def test_review_verified_unique_and_roundup(db,shop):
    s,u,p,skus=shop;reviews=ReviewService(db)
    for i,rating in enumerate([4,4,5]):
        c=s.add_item(u[i],skus[0],1,operation_id='add')
        order=s.checkout_cart(u[i],checkout_id='buy',cart_id=c['_id'],expected_revision=c['revision'])
        line=db.order_items.find_one({'order_id':order['_id']})
        with pytest.raises(CartError): reviews.create_review(u[i],line['_id'],rating)
        db.orders.update_one({'_id':order['_id']},{'$set':{'shipping_status':'delivered'}})
        review=reviews.create_review(u[i],line['_id'],rating)
        assert reviews.create_review(u[i],line['_id'],rating)['_id']==review['_id']
        with pytest.raises(CartConflict): reviews.create_review(u[i],line['_id'],1)
        if i==0:
            product=db.products.find_one({'_id':p[0]})
            assert product['rating_status']=='ACTUAL' and product['rating_count']==1 and product['rating_sum']==4
    product=db.products.find_one({'_id':p[0]})
    assert product['rating_count']==3 and product['rating_sum']==13 and product['average_rating_display']==4.4
    assert product['rating_default_value'] is None


def test_inventory_and_policy():
    with connect() as c:
        report=verify_complete(c.vibecart_ai)
        assert len(report)==27 and sum(len(r['indexes']) for r in report)==86
        policy=c.vibecart_ai.system_configs.find_one({'config_key':'recommendation_policy'})['settings']
        assert policy['weights']=={'PURCHASE':4,'ADD_TO_CART':3,'SEARCH':2,'PRODUCT_VIEW':1}
        assert policy['major_score_cap']==70 and policy['minor_score_cap']==30
