"""Live Atlas integration tests using uniquely identified, explicitly removed fixtures."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from copy import deepcopy
import pytest
from bson import ObjectId, Decimal128
from pymongo.errors import OperationFailure

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.cart_service import CartService, CartError, CartConflict
from bootstrap_schema import connect
from schema_current import verify_current


@pytest.fixture
def env():
    with connect('.env') as client:
        db=client.vibecart_ai
        now=datetime.now(timezone.utc)
        tag='cart-test-'+uuid4().hex
        user_ids=[ObjectId() for _ in range(3)]
        product_ids=[ObjectId() for _ in range(2)]
        cid=ObjectId()
        common={'schema_version':2,'created_at':now,'updated_at':now}
        try:
            db.categories.insert_one({**common,'_id':cid,'name':tag,'slug':tag,
                'description':None,'sort_order':0,'is_active':True})
            for i,uid in enumerate(user_ids):
                db.users.insert_one({**common,'_id':uid,'display_name':tag,
                    'email':f'{tag}-{i}@example.invalid','auth_provider':'local',
                    'password_hash':'fixture-not-a-login-account','firebase_uid':None,
                    'role':'customer','is_active':True,'preferences':{'category_ids':[],
                    'tags':[],'budget_min':None,'budget_max':None,'updated_at':None}})
            for i,pid in enumerate(product_ids):
                db.products.insert_one({**common,'_id':pid,'category_id':cid,'name':tag,
                    'description':'Temporary cart integration fixture','sku':f'{tag}-{i}'.upper(),
                    'brand':None,'size':None,'color':None,'price':Decimal128('10.00'),
                    'sale_price':None,'currency':'TWD','stock_quantity':20,'safety_stock':0,
                    'tags':[],'image_urls':[],'is_active':True})
            yield db,CartService(db,enable_checkout=True),user_ids,product_ids
        finally:
            # Exact generated IDs only; never broad deletion of real data.
            owner={'user_id':{'$in':user_ids}}
            for name in ('cart_events','carts','orders','user_events'):
                db[name].delete_many(owner)
                assert db[name].count_documents(owner)==0
            db.products.delete_many({'_id':{'$in':product_ids}})
            db.users.delete_many({'_id':{'$in':user_ids}})
            db.categories.delete_one({'_id':cid})


def test_lifecycle_prices_events_and_idempotency(env):
    db,s,users,products=env
    uid,pid=users[0],products[0]
    assert s.get_active_cart(uid) is None
    c=s.add_item(uid,pid,1,operation_id='add-1')
    added=c['items'][0]['added_at']
    c=s.add_item(uid,pid,1,operation_id='add-1')
    assert c['items'][0]['quantity']==1
    with pytest.raises(CartConflict):
        s.add_item(uid,pid,2,operation_id='add-1')
    c=s.add_item(uid,pid,2,operation_id='add-2')
    assert c['items'][0]['quantity']==3
    db.products.update_one({'_id':pid},{'$set':{'sale_price':Decimal128('8.00')}})
    c=s.update_quantity(uid,pid,2,operation_id='qty-1')
    assert c['items'][0]['added_at']==added
    assert c['items'][0]['price_snapshot']==Decimal128('8.00')
    c=s.remove_item(uid,pid,operation_id='remove-1')
    assert c['items']==[]
    assert db.cart_events.count_documents({'cart_id':c['_id']})==4
    assert s.get_active_cart(uid)['_id']==c['_id']
    assert db.orders.count_documents({'user_id':uid})==0


@pytest.mark.parametrize('qty',[0,-1,100,True,1.5,'2'])
def test_invalid_quantity(env,qty):
    db,s,u,p=env
    with pytest.raises(CartError):
        s.add_item(u[0],p[0],qty,operation_id='invalid')
    assert db.carts.count_documents({'user_id':u[0]})==0
    assert db.cart_events.count_documents({'user_id':u[0]})==0


def test_unavailable_product_and_inactive_user(env):
    db,s,u,p=env
    with pytest.raises(CartError):
        s.add_item(u[0],ObjectId(),1,operation_id='missing')
    db.products.update_one({'_id':p[0]},{'$set':{'is_active':False}})
    with pytest.raises(CartError):
        s.add_item(u[0],p[0],1,operation_id='inactive-product')
    db.users.update_one({'_id':u[0]},{'$set':{'is_active':False}})
    with pytest.raises(CartError):
        s.add_item(u[0],p[1],1,operation_id='inactive-user')
    assert db.carts.count_documents({'user_id':u[0]})==0


def test_checkout_history_reprice_retry_and_new_cart(env):
    db,s,u,p=env
    c=s.add_item(u[0],p[0],2,operation_id='add')
    with pytest.raises(CartError):
        CartService(db).checkout_cart(u[0],checkout_id='disabled',cart_id=c['_id'],expected_revision=c['revision'])
    db.products.update_one({'_id':p[0]},{'$set':{'sale_price':Decimal128('0.00')}})
    args={'checkout_id':'checkout','cart_id':c['_id'],'expected_revision':c['revision']}
    order=s.checkout_cart(u[0],**args)
    assert order['total_amount']==Decimal128('0.00')
    assert s.checkout_cart(u[0],**args)['_id']==order['_id']
    with pytest.raises(CartConflict):
        s.checkout_cart(u[0],**{**args,'expected_revision':c['revision']+1})
    history=db.carts.find_one({'_id':c['_id']})
    assert history['status']=='converted' and len(history['items'])==1
    assert history['items'][0]['price_snapshot']==Decimal128('10.00')
    assert db.cart_events.count_documents({'cart_id':c['_id'],'event_type':'CHECKOUT'})==1
    assert db.user_events.count_documents({'order_id':order['_id'],'event_type':'purchase'})==1
    assert db.products.find_one({'_id':p[0]})['stock_quantity']==18
    new=s.add_item(u[0],p[0],1,operation_id='next-cart')
    assert new['_id']!=c['_id'] and new['status']=='active'


def test_checkout_ownership_stale_revision_and_rollback(env):
    db,s,u,p=env
    c=s.add_item(u[0],p[0],1,operation_id='first')
    old=c['revision']
    c=s.add_item(u[0],p[1],1,operation_id='second')
    with pytest.raises(CartConflict):
        s.checkout_cart(u[1],checkout_id='other-owner',cart_id=c['_id'],expected_revision=c['revision'])
    with pytest.raises(CartConflict):
        s.checkout_cart(u[0],checkout_id='stale',cart_id=c['_id'],expected_revision=old)
    db.products.update_one({'_id':p[1]},{'$set':{'stock_quantity':0}})
    with pytest.raises(CartError):
        s.checkout_cart(u[0],checkout_id='failure',cart_id=c['_id'],expected_revision=c['revision'])
    assert db.products.find_one({'_id':p[0]})['stock_quantity']==20
    assert s.get_active_cart(u[0])['revision']==c['revision']
    assert db.orders.count_documents({'user_id':u[0]})==0
    assert db.cart_events.count_documents({'user_id':u[0],'event_type':'CHECKOUT'})==0


def test_concurrent_adds_and_same_key(env):
    db,s,u,p=env
    with ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(lambda _:s.add_item(u[0],p[0],1,operation_id='same'),range(2)))
    assert values[0]['_id']==values[1]['_id']
    assert s.get_active_cart(u[0])['items'][0]['quantity']==1
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda k:s.add_item(u[0],p[0],1,operation_id=k),['one','two']))
    assert s.get_active_cart(u[0])['items'][0]['quantity']==3
    assert db.carts.count_documents({'user_id':u[0],'status':'active'})==1
    assert db.cart_events.count_documents({'user_id':u[0]})==3


def test_two_customers_last_stock(env):
    db,s,u,p=env
    db.products.update_one({'_id':p[0]},{'$set':{'stock_quantity':1}})
    carts=[s.add_item(uid,p[0],1,operation_id='add') for uid in u[:2]]
    def buy(index):
        try:
            return s.checkout_cart(u[index],checkout_id='buy',cart_id=carts[index]['_id'],expected_revision=carts[index]['revision'])
        except CartError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(buy,range(2)))
    assert sum(o is not None for o in outcomes)==1
    assert db.products.find_one({'_id':p[0]})['stock_quantity']==0
    assert db.orders.count_documents({'user_id':{'$in':u}})==1


def test_abandonment_and_history(env):
    db,s,u,p=env
    c=s.add_item(u[0],p[0],1,operation_id='add')
    cutoff=datetime.now(timezone.utc)-timedelta(days=7)
    with pytest.raises(CartConflict):
        s.abandon_cart(u[0],cart_id=c['_id'],inactive_before=cutoff,operation_id='abandon')
    db.carts.update_one({'_id':c['_id']},{'$set':{'updated_at':cutoff-timedelta(days=1)}})
    a=s.abandon_cart(u[0],cart_id=c['_id'],inactive_before=cutoff,operation_id='abandon')
    assert a['status']=='abandoned' and a['items']
    assert s.abandon_cart(u[0],cart_id=c['_id'],inactive_before=cutoff,operation_id='abandon')['_id']==a['_id']
    assert db.cart_events.count_documents({'cart_id':c['_id'],'event_type':'ABANDON'})==1
    assert s.add_item(u[0],p[0],1,operation_id='new')['_id']!=a['_id']


def test_database_constraints_and_future_event(env):
    db,s,u,p=env
    c=s.add_item(u[0],p[0],1,operation_id='add')
    def attempt(document,collection,code=None):
        with db.client.start_session() as session:
            session.start_transaction()
            try:
                if code:
                    with pytest.raises(OperationFailure) as err:
                        db[collection].insert_one(document,session=session)
                    assert err.value.code==code
                else:
                    db[collection].insert_one(document,session=session)
            finally:
                if session.in_transaction:
                    session.abort_transaction()
    other=deepcopy(c)
    other['_id']=ObjectId()
    attempt(other,'carts',11000)
    other['status']='converted'
    attempt(other,'carts')
    other['items'][0]['price_snapshot']=1.0
    attempt(other,'carts',121)
    e=db.cart_events.find_one({'cart_id':c['_id']})
    e.update(_id=ObjectId(),operation_id='future',event_type='SAVE_FOR_LATER')
    attempt(e,'cart_events')
    e.update(event_type='REMOVE',quantity_after=2)
    attempt(e,'cart_events',121)


def test_current_schema():
    with connect() as client:
        report=verify_current(client.vibecart_ai)
        assert len(report)==14
        assert sum(len(r['indexes']) for r in report)==45
