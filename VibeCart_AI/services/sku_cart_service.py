"""Current v4 SKU cart service. The old product-as-SKU service is historical."""
from decimal import Decimal
from bson import ObjectId,Decimal128
from .cart_service import CartService as LegacyCartService,CartError,CartConflict,oid,quantity,key,fingerprint,utcnow


class CartService(LegacyCartService):
    def _user(self,uid,session=None):
        if not self.db.users.find_one({'_id':uid,'schema_version':4,'status':'active','is_active':True},session=session):
            raise CartError('Active schema v4 user required')

    def _sku(self,sid,qty,s):
        sku=self.db.product_skus.find_one({'_id':sid,'status':'active'},session=s)
        if not sku or sku['available_quantity']<qty:
            raise CartError('SKU unavailable or insufficient available stock')
        product=self.db.products.find_one({'_id':sku['product_id'],'status':'active'},session=s)
        if not product:
            raise CartError('Product unavailable')
        return sku,product

    def _event(self,cart,kind,operation_id,request_hash,now,*,pid=None,before=None,after=None,price=None,metadata=None,sku_id=None):
        event=super()._event(cart,kind,operation_id,request_hash,now,pid=pid,before=before,after=after,price=price,metadata=metadata)
        event.update(schema_version=4,sku_id=sku_id,event_id='cart:'+str(event['_id']))
        return event

    def _behavior(self,uid,product,qty,kind,event_id,now,cart_id,order_id=None):
        return {'_id':ObjectId(),'schema_version':4,'event_id':event_id,'user_id':uid,'anonymous_id':None,
            'session_id':'cart:'+str(cart_id),'event_type':kind,'product_id':product['_id'],
            'major_category_id':product['major_category_id'],'minor_category_id':product['minor_category_id'],
            'quantity':qty,'order_id':order_id,'cart_id':cart_id,'search_query':None,'source':'organic',
            'recommendation_id':None,'event_at':now,'score_version':1,'processed_at':None,'metadata':{},'created_at':now}

    def _mutate(self,user_id,sku_id,qty,operation_id,kind):
        uid,sid=oid(user_id),oid(sku_id)
        operation_id=key(operation_id); request_hash=fingerprint([kind,str(sid),qty])
        def action(s):
            self._user(uid,s)
            prior=self._replay(uid,operation_id,request_hash,s)
            if prior: return self.db.carts.find_one({'_id':prior['cart_id'],'user_id':uid},session=s)
            now=utcnow()
            cart=self.db.carts.find_one({'user_id':uid,'status':'active'},session=s)
            if not cart:
                if kind!='ADD': raise CartError('No active cart')
                cart={'_id':ObjectId(),'schema_version':4,'user_id':uid,'status':'active','revision':0,
                      'items':[],'created_at':now,'updated_at':now}
                self.db.carts.insert_one(cart,session=s)
            item=next((i for i in cart['items'] if i['sku_id']==sid),None)
            before=item['quantity'] if item else 0
            if kind!='ADD' and not item: raise CartError('SKU not in cart')
            after=0 if kind=='REMOVE' else before+qty if kind=='ADD' else qty
            if after==before: raise CartError('Quantity unchanged')
            if kind=='REMOVE':
                price=item['price_snapshot']; pid=item['product_id']
                cart['items']=[i for i in cart['items'] if i['sku_id']!=sid]
            else:
                quantity(after)
                sku,product=self._sku(sid,after,s); price=sku['price'];pid=product['_id']
                if item:
                    if item['product_id']!=pid: raise CartConflict('SKU product association changed')
                    item.update(quantity=after,price_snapshot=price,updated_at=now)
                else:
                    if len(cart['items'])>=20: raise CartError('At most 20 distinct SKUs')
                    cart['items'].append({'product_id':pid,'sku_id':sid,'quantity':after,'price_snapshot':price,'added_at':now,'updated_at':now})
            result=self.db.carts.update_one({'_id':cart['_id'],'status':'active','revision':cart['revision']},
                {'$set':{'items':cart['items'],'updated_at':now},'$inc':{'revision':1}},session=s)
            if result.modified_count!=1: raise CartConflict('Cart changed')
            event=self._event(cart,kind,operation_id,request_hash,now,pid=pid,sku_id=sid,before=before,after=after,price=price)
            self.db.cart_events.insert_one(event,session=s)
            if kind=='ADD':
                self.db.behavior_events.insert_one(self._behavior(uid,product,qty,'ADD_TO_CART',
                    'cart-add:'+str(event['_id']),now,cart['_id']),session=s)
            cart.update(revision=cart['revision']+1,updated_at=now)
            return cart
        return self._run(action)

    def add_item(self,user_id,sku_id,quantity_value,*,operation_id):
        return self._mutate(user_id,sku_id,quantity(quantity_value),operation_id,'ADD')

    def update_quantity(self,user_id,sku_id,quantity_value,*,operation_id):
        return self._mutate(user_id,sku_id,quantity(quantity_value),operation_id,'QTY_CHANGE')

    def remove_item(self,user_id,sku_id,*,operation_id):
        return self._mutate(user_id,sku_id,None,operation_id,'REMOVE')

    def checkout_cart(self,user_id,*,checkout_id,cart_id,expected_revision):
        if not self.enable_checkout: raise CartError('Demo checkout disabled')
        uid,cid=oid(user_id),oid(cart_id);checkout_id=key(checkout_id)
        if type(expected_revision) is not int or expected_revision<0: raise CartError('Cart revision required')
        request_hash=fingerprint(['CHECKOUT',str(cid),expected_revision])
        def action(s):
            self._user(uid,s)
            prior=self._replay(uid,checkout_id,request_hash,s)
            if prior: return self.db.orders.find_one({'_id':prior['metadata']['order_id'],'user_id':uid},session=s)
            cart=self.db.carts.find_one({'_id':cid,'user_id':uid,'status':'active','revision':expected_revision},session=s)
            if not cart or not cart['items']: raise CartConflict('Cart empty, stale, or converted')
            now=utcnow();order_id=ObjectId();lines=[];total=Decimal('0');purchases={}
            for item in cart['items']:
                sku,product=self._sku(item['sku_id'],item['quantity'],s)
                if product['_id']!=item['product_id']: raise CartConflict('SKU product association changed')
                qty=item['quantity']; subtotal=sku['price'].to_decimal()*qty;total+=subtotal
                available=sku['available_quantity']-qty
                stock_status='out_of_stock' if available==0 else 'low_stock' if available<=sku['safety_stock'] else 'in_stock'
                result=self.db.product_skus.update_one({'_id':sku['_id'],'status':'active','available_quantity':{'$gte':qty}},
                    {'$inc':{'stock_quantity':-qty,'available_quantity':-qty},'$set':{'stock_status':stock_status,'updated_at':now}},session=s)
                if result.modified_count!=1: raise CartConflict('Stock changed')
                lines.append({'_id':ObjectId(),'schema_version':4,'order_id':order_id,'user_id':uid,
                    'product_id':product['_id'],'sku_id':sku['_id'],'product_code_snapshot':product['product_code'],
                    'product_name_snapshot':product['product_name'],'major_category_id_snapshot':product['major_category_id'],
                    'minor_category_id_snapshot':product['minor_category_id'],'quantity':qty,'unit_price':sku['price'],
                    'line_total':Decimal128(subtotal),'created_at':now})
                if product['_id'] not in purchases: purchases[product['_id']]=[product,0]
                purchases[product['_id']][1]+=qty
            order={'_id':order_id,'schema_version':4,'user_id':uid,'order_number':'VC'+str(order_id).upper(),
                'status':'confirmed','payment_status':'paid','shipping_status':'pending','subtotal':Decimal128(total),
                'shipping_fee':Decimal128('0'),'total_amount':Decimal128(total),'ordered_at':now,'completed_at':None,
                'checkout_id':checkout_id,'request_hash':fingerprint(sorted([(str(i['sku_id']),i['quantity']) for i in cart['items']])),
                'is_demo':True,'currency':'TWD','paid_at':now,'discount_amount':Decimal128('0'),'created_at':now,'updated_at':now}
            self.db.orders.insert_one(order,session=s)
            self.db.order_items.insert_many(lines,session=s)
            for product,qty in purchases.values():
                self.db.behavior_events.insert_one(self._behavior(uid,product,qty,'PURCHASE',
                    'purchase:'+str(order_id)+':'+str(product['_id']),now,cid,order_id),session=s)
            self.db.cart_events.insert_one(self._event(cart,'CHECKOUT',checkout_id,request_hash,now,metadata={'order_id':order_id}),session=s)
            result=self.db.carts.update_one({'_id':cid,'status':'active','revision':expected_revision},
                {'$set':{'status':'converted','updated_at':now},'$inc':{'revision':1}},session=s)
            if result.modified_count!=1: raise CartConflict('Cart changed')
            return order
        return self._run(action)
