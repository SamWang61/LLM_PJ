"""Transactional cart state, immutable event history, and Demo checkout.

Call only with the authenticated user's ID; never take owner IDs from request bodies.
All mutations require a stable operation key. Reuse it only for the same request.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import time
from bson import ObjectId, Decimal128
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


class CartError(ValueError):
    pass


class CartConflict(CartError):
    pass


def oid(value):
    try:
        return value if isinstance(value,ObjectId) else ObjectId(value)
    except Exception as exc:
        raise CartError('Invalid ObjectId') from exc


def quantity(value):
    if type(value) is not int or not 1 <= value <= 99:
        raise CartError('Quantity must be an integer from 1 to 99; use remove_item to remove')
    return value


def key(value):
    if not isinstance(value,str) or not value.strip() or len(value)>128:
        raise CartError('A stable operation_id of 1..128 characters is required')
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def utcnow():
    now=datetime.now(timezone.utc)
    return now.replace(microsecond=(now.microsecond//1000)*1000)


class CartService:
    def __init__(self, db, *, enable_checkout=False):
        self.db=db
        self.enable_checkout=enable_checkout

    def _user(self, uid, session=None):
        if not self.db.users.find_one({'_id':uid,'is_active':True},session=session):
            raise CartError('Active user required')

    def _run(self, callback):
        # Partial unique index handles concurrent creation; retry the entire transaction.
        for attempt in range(4):
            try:
                with self.db.client.start_session() as session:
                    return session.with_transaction(callback,read_concern=ReadConcern('snapshot'),
                                                     write_concern=WriteConcern('majority'))
            except DuplicateKeyError:
                if attempt==3:
                    raise CartConflict('Concurrent operation; retry using the same key') from None
                time.sleep(0.025*(attempt+1))

    def get_active_cart(self,user_id):
        uid=oid(user_id)
        self._user(uid)
        return self.db.carts.find_one({'user_id':uid,'status':'active'})

    def _product(self,pid,qty,s):
        p=self.db.products.find_one({'_id':pid,'is_active':True},session=s)
        if not p or p['stock_quantity']<qty:
            raise CartError('Product unavailable or insufficient stock')
        return p

    @staticmethod
    def _price(product):
        return product['sale_price'] if product['sale_price'] is not None else product['price']

    def _replay(self,uid,operation_id,request_hash,s):
        e=self.db.cart_events.find_one({'user_id':uid,'operation_id':operation_id},session=s)
        if e and e['request_hash']!=request_hash:
            raise CartConflict('Operation key reused with different content')
        return e

    def _event(self,cart,kind,operation_id,request_hash,now,*,pid=None,before=None,after=None,price=None,metadata=None):
        return {'_id':ObjectId(),'schema_version':3,'cart_id':cart['_id'],'user_id':cart['user_id'],
                'operation_id':operation_id,'request_hash':request_hash,'event_type':kind,
                'product_id':pid,'quantity_before':before,'quantity_after':after,
                'price_snapshot':price,'event_at':now,'created_at':now,'metadata':metadata or {}}

    def _mutate(self,user_id,product_id,qty,operation_id,kind):
        uid,pid=oid(user_id),oid(product_id)
        operation_id=key(operation_id)
        request_hash=fingerprint([kind,str(pid),qty])
        def action(s):
            self._user(uid,s)
            prior=self._replay(uid,operation_id,request_hash,s)
            if prior:
                return self.db.carts.find_one({'_id':prior['cart_id'],'user_id':uid},session=s)
            now=utcnow()
            cart=self.db.carts.find_one({'user_id':uid,'status':'active'},session=s)
            if not cart:
                if kind!='ADD':
                    raise CartError('No active cart')
                cart={'_id':ObjectId(),'schema_version':3,'user_id':uid,'status':'active',
                      'revision':0,'items':[],'created_at':now,'updated_at':now}
                self.db.carts.insert_one(cart,session=s)
            item=next((i for i in cart['items'] if i['product_id']==pid),None)
            before=item['quantity'] if item else 0
            if kind!='ADD' and not item:
                raise CartError('Product not in active cart')
            after=0 if kind=='REMOVE' else before+qty if kind=='ADD' else qty
            if after==before:
                raise CartError('Quantity unchanged')
            if kind=='REMOVE':
                price=item['price_snapshot']
                cart['items']=[i for i in cart['items'] if i['product_id']!=pid]
            else:
                quantity(after)
                p=self._product(pid,after,s)
                price=self._price(p)
                if item:
                    item.update(quantity=after,price_snapshot=price,updated_at=now)
                else:
                    if len(cart['items'])>=20:
                        raise CartError('At most 20 distinct products')
                    cart['items'].append({'product_id':pid,'quantity':after,'price_snapshot':price,
                                          'added_at':now,'updated_at':now})
            result=self.db.carts.update_one({'_id':cart['_id'],'user_id':uid,'status':'active','revision':cart['revision']},
                {'$set':{'items':cart['items'],'updated_at':now},'$inc':{'revision':1}},session=s)
            if result.modified_count!=1:
                raise CartConflict('Cart changed')
            self.db.cart_events.insert_one(self._event(cart,kind,operation_id,request_hash,now,
                pid=pid,before=before,after=after,price=price),session=s)
            cart.update(updated_at=now,revision=cart['revision']+1)
            return cart
        return self._run(action)

    def add_item(self,user_id,product_id,quantity_value,*,operation_id):
        return self._mutate(user_id,product_id,quantity(quantity_value),operation_id,'ADD')

    def remove_item(self,user_id,product_id,*,operation_id):
        return self._mutate(user_id,product_id,None,operation_id,'REMOVE')

    def update_quantity(self,user_id,product_id,quantity_value,*,operation_id):
        return self._mutate(user_id,product_id,quantity(quantity_value),operation_id,'QTY_CHANGE')

    def checkout_cart(self,user_id,*,checkout_id,cart_id,expected_revision):
        if not self.enable_checkout:
            raise CartError('Demo checkout disabled')
        uid,cid=oid(user_id),oid(cart_id)
        checkout_id=key(checkout_id)
        if type(expected_revision) is not int or expected_revision<0:
            raise CartError('Expected cart revision required')
        request_hash=fingerprint(['CHECKOUT',str(cid),expected_revision])
        def action(s):
            self._user(uid,s)
            prior=self._replay(uid,checkout_id,request_hash,s)
            if prior:
                return self.db.orders.find_one({'_id':prior['metadata']['order_id'],'user_id':uid},session=s)
            cart=self.db.carts.find_one({'_id':cid,'user_id':uid,'status':'active','revision':expected_revision},session=s)
            if not cart or not cart['items']:
                raise CartConflict('Cart empty, changed, or no longer active')
            now=utcnow()
            lines=[]
            total=Decimal('0.00')
            for item in cart['items']:
                p=self._product(item['product_id'],item['quantity'],s)
                price=self._price(p)
                subtotal=price.to_decimal()*item['quantity']
                total+=subtotal
                stock=self.db.products.update_one({'_id':p['_id'],'is_active':True,'stock_quantity':{'$gte':item['quantity']}},
                    {'$inc':{'stock_quantity':-item['quantity']},'$set':{'updated_at':now}},session=s)
                if stock.modified_count!=1:
                    raise CartConflict('Stock changed')
                lines.append({'product_id':p['_id'],'product_name':p['name'],'sku':p['sku'],
                              'size':p['size'],'color':p['color'],'unit_price':price,
                              'quantity':item['quantity'],'subtotal_amount':Decimal128(subtotal)})
            order_id=ObjectId()
            order={'_id':order_id,'schema_version':2,'order_number':'VC'+str(order_id).upper(),
                   'user_id':uid,'checkout_id':checkout_id,'request_hash':fingerprint(sorted(
                       [(str(i['product_id']),i['quantity']) for i in cart['items']])),
                   'status':'confirmed','payment_status':'paid','is_demo':True,'currency':'TWD',
                   'items':lines,'subtotal_amount':Decimal128(total),'discount_amount':Decimal128('0'),
                   'shipping_fee':Decimal128('0'),'total_amount':Decimal128(total),'shipping_address':None,
                   'paid_at':now,'created_at':now,'updated_at':now}
            self.db.orders.insert_one(order,session=s)
            self.db.cart_events.insert_one(self._event(cart,'CHECKOUT',checkout_id,request_hash,now,
                                                       metadata={'order_id':order_id}),session=s)
            self.db.user_events.insert_one({'_id':ObjectId(),'schema_version':2,
                'event_id':'checkout:'+str(order_id),'user_id':uid,'session_id':'cart:'+str(cid),
                'event_type':'purchase','product_id':None,'order_id':order_id,'recommendation_id':None,
                'search_query':None,'event_metadata':{},'created_at':now},session=s)
            result=self.db.carts.update_one({'_id':cid,'user_id':uid,'status':'active','revision':expected_revision},
                {'$set':{'status':'converted','updated_at':now},'$inc':{'revision':1}},session=s)
            if result.modified_count!=1:
                raise CartConflict('Cart changed')
            return order
        return self._run(action)

    def abandon_cart(self,user_id,*,cart_id,inactive_before,operation_id):
        """Trusted scheduled job only; caller supplies its explicit abandonment cutoff."""
        uid,cid=oid(user_id),oid(cart_id)
        operation_id=key(operation_id)
        if not isinstance(inactive_before,datetime) or inactive_before.tzinfo is None:
            raise CartError('Timezone-aware abandonment cutoff required')
        if inactive_before>datetime.now(timezone.utc):
            raise CartError('Abandonment cutoff cannot be in the future')
        request_hash=fingerprint(['ABANDON',str(cid),inactive_before.isoformat()])
        def action(s):
            self._user(uid,s)
            if self._replay(uid,operation_id,request_hash,s):
                return self.db.carts.find_one({'_id':cid,'user_id':uid},session=s)
            cart=self.db.carts.find_one({'_id':cid,'user_id':uid,'status':'active',
                                        'updated_at':{'$lt':inactive_before}},session=s)
            if not cart:
                raise CartConflict('Cart is not eligible for abandonment')
            now=utcnow()
            result=self.db.carts.update_one({'_id':cid,'status':'active','revision':cart['revision']},
                {'$set':{'status':'abandoned','updated_at':now},'$inc':{'revision':1}},session=s)
            if result.modified_count!=1:
                raise CartConflict('Cart changed')
            self.db.cart_events.insert_one(self._event(cart,'ABANDON',operation_id,request_hash,now),session=s)
            cart.update(status='abandoned',updated_at=now,revision=cart['revision']+1)
            return cart
        return self._run(action)
