"""Verified order-line reviews and exact upward-rounded product rating aggregates."""
from decimal import Decimal,ROUND_CEILING
from bson import ObjectId
from .sku_cart_service import CartService
from .cart_service import CartError,CartConflict,oid,utcnow


class ReviewService(CartService):
    def create_review(self,user_id,order_item_id,rating,*,title='',content=''):
        uid,lid=oid(user_id),oid(order_item_id)
        if type(rating) is not int or not 1<=rating<=5: raise CartError('Rating must be an integer from 1 to 5')
        if not isinstance(title,str) or len(title)>200 or not isinstance(content,str) or len(content)>8000:
            raise CartError('Invalid review text')
        def action(s):
            self._user(uid,s)
            previous=self.db.product_reviews.find_one({'user_id':uid,'order_item_id':lid},session=s)
            if previous:
                if (previous['rating'],previous['review_title'],previous['review_content'])!=(rating,title,content):
                    raise CartConflict('An order item may only be reviewed once')
                return previous
            line=self.db.order_items.find_one({'_id':lid,'user_id':uid},session=s)
            if not line: raise CartError('Purchased order item required')
            order=self.db.orders.find_one({'_id':line['order_id'],'user_id':uid,'payment_status':'paid',
                'status':{'$ne':'cancelled'},'$or':[{'status':'completed'},{'shipping_status':'delivered'}]},session=s)
            if not order: raise CartError('Order must be completed or delivered')
            product=self.db.products.find_one({'_id':line['product_id']},session=s)
            if not product: raise CartError('Product not found')
            now=utcnow()
            review={'_id':ObjectId(),'schema_version':4,'user_id':uid,'product_id':product['_id'],
                'order_id':order['_id'],'order_item_id':lid,'rating':rating,'review_title':title,
                'review_content':content,'verified_purchase':True,'status':'published','created_at':now,'updated_at':now}
            self.db.product_reviews.insert_one(review,session=s)
            distribution={f'star_{i}':0 for i in range(1,6)}
            for row in self.db.product_reviews.aggregate([
                {'$match':{'product_id':product['_id'],'status':'published'}},
                {'$group':{'_id':'$rating','count':{'$sum':1}}}],session=s):
                distribution['star_'+str(row['_id'])]=row['count']
            count=sum(distribution.values()); total=sum(i*distribution[f'star_{i}'] for i in range(1,6))
            mean=Decimal(total)/Decimal(count)
            display=mean.quantize(Decimal('0.1'),rounding=ROUND_CEILING)
            self.db.products.update_one({'_id':product['_id']},{'$set':{'rating_status':'ACTUAL',
                'rating_default_value':None,'rating_sum':total,'rating_count':count,'average_rating_raw':float(mean),
                'average_rating_display':float(display),'rating_distribution':distribution,'updated_at':now}},session=s)
            return review
        return self._run(action)
