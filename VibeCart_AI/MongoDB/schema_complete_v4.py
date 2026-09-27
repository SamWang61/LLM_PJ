"""2026-09-18 Complete Schema v1.0: 19 core + 8 preserved collections.

ObjectId references, Decimal128 currency, UTC BSON dates. Historical migrations
remain immutable; all redesigned/new core documents carry schema_version=4.
"""
from copy import deepcopy
from datetime import datetime,timezone
from bson import Decimal128
from pymongo import IndexModel
from bootstrap_schema import typ,string,integer,enum,obj,OID,NOID,DATE,NDATE,BOOL,MONEY,NMONEY,HASH
from schema_current import SCHEMAS as PREVIOUS,INDEXES as PREVIOUS_INDEXES

SCHEMAS=deepcopy(PREVIOUS)
INDEXES=deepcopy(PREVIOUS_INDEXES)
CORE=['users','products','product_skus','product_reviews','product_repurchase_stats','categories','brands',
      'orders','order_items','carts','cart_events','behavior_events','user_preference_scores','cross_category_rules',
      'product_purchase_sequences','recommendation_pools','first_member_recommendations','recommendation_logs','system_configs']
CHANGED=['users','products','categories','orders','carts','cart_events']
PRESERVED=[n for n in PREVIOUS if n not in CHANGED]


def arr(item,maximum=None,minimum=0,unique=False):
    result={'bsonType':'array','items':item,'minItems':minimum,'uniqueItems':unique}
    if maximum is not None: result['maxItems']=maximum
    return result


def num(nullable=False,minimum=0,maximum=None):
    result=typ('double',nullable,minimum=minimum,maximum=maximum if maximum is not None else 1.7976931348623157e308)
    return result


def document(name,fields,created=True,updated=True):
    fields={'_id':OID,'schema_version':typ('int',enum=[4]),**fields}
    if created: fields['created_at']=DATE
    if updated: fields['updated_at']=DATE
    SCHEMAS[name]={'$jsonSchema':obj(fields)}


def rule(name,expr):
    SCHEMAS[name].setdefault('$and',[]).append({'$expr':expr})


def implies(condition,result): return {'$or':[{'$not':[condition]},result]}
def unique_items(path): return {'$eq':[{'$size':'$items'},{'$size':{'$setUnion':[path,[]]}}]}
def money_expr(path,nullable=False):
    check={'$and':[{'$lte':[path,Decimal128('9.999999999999999999999999999999999E+6144')]},
                   {'$eq':[path,{'$round':[path,2]}]}]}
    return {'$or':[{'$eq':[path,None]},check]} if nullable else check


ACTIVE=enum('active','inactive')
TEXTS=arr(string(100,minimum=1),unique=True)
PATH=arr(string(100,minimum=1),2,1)
RATING=num(minimum=1,maximum=5)
RATE=num(maximum=1)
CODE=string(100,minimum=1)

# Preserve login and explicit preferences while adding the new member lifecycle.
users=deepcopy(PREVIOUS['users']['$jsonSchema']['properties'])
for k in ('_id','schema_version','created_at','updated_at'): users.pop(k)
users.update(status=ACTIVE,member_level=string(50,minimum=1),registered_at=DATE,
             first_recommendation_generated_at=NDATE,last_login_at=NDATE)
document('users',users)
SCHEMAS['users']['$and']=deepcopy(PREVIOUS['users'].get('$and',[]))
rule('users',{'$eq':['$is_active',{'$eq':['$status','active']}]})

document('categories',{'category_code':CODE,'name':string(100,minimum=1),'level':typ('int',enum=[1,2]),
    'parent_id':NOID,'path':PATH,'status':ACTIVE,'sort_order':integer()})
rule('categories',{'$eq':[{'$size':'$path'},'$level']})
rule('categories',{'$eq':[{'$arrayElemAt':['$path',-1]},'$category_code']})
rule('categories',{'$eq':[{'$eq':['$level',1]},{'$eq':['$parent_id',None]}]})

document('brands',{'brand_code':CODE,'name':string(100,minimum=1),'description':string(1000,True),'status':ACTIVE})

document('products',{
    'product_code':CODE,'product_name':string(200,minimum=1),'product_aliases':TEXTS,'brand_id':NOID,
    'major_category_id':OID,'minor_category_id':OID,'category_path':arr(string(100,minimum=1),2,2),
    'summary':string(1000,minimum=1),'description':string(5000,minimum=1),'usage_scenarios':TEXTS,
    'target_segments':TEXTS,'product_tags':TEXTS,'status':enum('active','inactive','draft'),
    'is_ai_recommendable':BOOL,'image_urls':arr(string(pattern=r'^(https://|/(?!/))'),10),
    'shipping_profile_id':typ(['objectId','string','null']),
    'rating_status':enum('DEFAULT','ACTUAL'),'rating_default_value':num(True,1,5),
    'rating_sum':integer(),'rating_count':integer(),'average_rating_raw':num(True,1,5),
    'average_rating_display':RATING,'rating_distribution':obj({f'star_{i}':integer() for i in range(1,6)}),
    'product_lifecycle_type':enum('consumable','durable'),'replenishment_enabled':BOOL,
    'expected_repurchase_interval_days':integer(True,minimum=1),'expected_purchase_frequency_year':num(True),
    'minimum_repeat_frequency_year':num(),'replenishment_basis':enum('category_benchmark','historical'),
    'replenishment_confidence':RATE,'repeat_purchase_rate_12m':num(True,0,1),
    'repeat_customer_count_12m':integer(),'unique_buyer_count_12m':integer(),'order_count_12m':integer(),
    'avg_purchase_frequency_12m':num(True),'median_repurchase_interval_days':num(True),
    'last_repurchase_calculated_at':NDATE})
distribution=[f'$rating_distribution.star_{i}' for i in range(1,6)]
rule('products',{'$eq':['$rating_count',{'$add':distribution}]})
rule('products',{'$eq':['$rating_sum',{'$add':[{'$multiply':[i,distribution[i-1]]} for i in range(1,6)]}]})
average={'$divide':[{'$toDecimal':'$rating_sum'},{'$toDecimal':'$rating_count'}]}
display={'$toDouble':{'$divide':[{'$ceil':{'$multiply':[average,10]}},10]}}
rule('products',{'$cond':[{'$eq':['$rating_count',0]},
    {'$and':[{'$eq':['$rating_status','DEFAULT']},{'$eq':['$rating_default_value',4.0]},
             {'$eq':['$average_rating_raw',None]},{'$eq':['$average_rating_display',4.0]}]},
    {'$and':[{'$eq':['$rating_status','ACTUAL']},{'$in':['$rating_default_value',[None,4.0]]},
             {'$eq':['$average_rating_raw',{'$toDouble':average}]},{'$eq':['$average_rating_display',display]}]}]})
rule('products',{'$lte':['$repeat_customer_count_12m','$unique_buyer_count_12m']})

document('product_skus',{'product_id':OID,'sku_code':CODE,
    'variant_attributes':{'bsonType':'object','additionalProperties':string(100)},
    'price':MONEY,'cost_price':NMONEY,'currency':enum('TWD'),'stock_quantity':integer(),
    'reserved_quantity':integer(),'available_quantity':integer(),'safety_stock':integer(),
    'stock_status':enum('in_stock','low_stock','out_of_stock'),'barcode':string(100,True),
    'weight_grams':integer(True),'status':ACTIVE})
rule('product_skus',{'$eq':['$available_quantity',{'$subtract':['$stock_quantity','$reserved_quantity']}]})
for field in ('price','cost_price'): rule('product_skus',money_expr('$'+field,field=='cost_price'))

document('product_reviews',{'product_id':OID,'user_id':OID,'order_id':OID,'order_item_id':OID,
    'rating':integer(minimum=1,maximum=5),'review_title':string(200),'review_content':string(8000),
    'verified_purchase':enum(True),'status':enum('pending','published','hidden','rejected')})

document('orders',{'user_id':OID,'order_number':CODE,'status':enum('pending','confirmed','shipping','completed','cancelled'),
    'payment_status':enum('unpaid','paid','failed','refunded'),
    'shipping_status':enum('pending','processing','shipped','delivered','returned','cancelled'),
    'subtotal':MONEY,'shipping_fee':MONEY,'total_amount':MONEY,'ordered_at':DATE,'completed_at':NDATE,
    'checkout_id':string(128,minimum=1),'request_hash':HASH,'is_demo':BOOL,'currency':enum('TWD'),
    'paid_at':NDATE,'discount_amount':MONEY})
rule('orders',{'$eq':['$total_amount',{'$add':[{'$subtract':['$subtotal','$discount_amount']},'$shipping_fee']}]})
rule('orders',{'$lte':['$discount_amount','$subtotal']})
rule('orders',implies({'$eq':['$payment_status','paid']},{'$ne':['$paid_at',None]}))
rule('orders',implies({'$eq':['$status','completed']},{'$ne':['$completed_at',None]}))
for f in ('subtotal','shipping_fee','total_amount','discount_amount'): rule('orders',money_expr('$'+f))
document('order_items',{'order_id':OID,'user_id':OID,'product_id':OID,'sku_id':OID,
    'product_code_snapshot':CODE,'product_name_snapshot':string(200,minimum=1),
    'major_category_id_snapshot':OID,'minor_category_id_snapshot':OID,
    'quantity':integer(minimum=1,maximum=99),'unit_price':MONEY,'line_total':MONEY},updated=False)
rule('order_items',{'$eq':['$line_total',{'$multiply':['$unit_price','$quantity']}]})
rule('order_items',money_expr('$unit_price'))

cart=deepcopy(PREVIOUS['carts']['$jsonSchema']['properties'])
for k in ('_id','schema_version','created_at','updated_at'): cart.pop(k)
cart['items']['items']['properties']['sku_id']=OID
cart['items']['items']['required'].append('sku_id')
document('carts',cart)
rule('carts',unique_items('$items.sku_id'))
rule('carts',{'$allElementsTrue':[{'$map':{'input':'$items','as':'i','in':money_expr('$$i.price_snapshot')}}]})
events=deepcopy(PREVIOUS['cart_events']['$jsonSchema']['properties'])
for k in ('_id','schema_version','created_at'): events.pop(k)
events.update(event_id=string(128,minimum=1),sku_id=NOID)
document('cart_events',events,updated=False)
SCHEMAS['cart_events']['$and']=deepcopy(PREVIOUS['cart_events']['$and'])
rule('cart_events',implies({'$in':['$event_type',['ADD','REMOVE','QTY_CHANGE']]},{'$ne':['$sku_id',None]}))

document('behavior_events',{'event_id':string(128,minimum=1),'user_id':NOID,'anonymous_id':string(128,True),
    'session_id':string(128,minimum=1),'event_type':enum('PURCHASE','ADD_TO_CART','SEARCH','PRODUCT_VIEW'),
    'product_id':NOID,'major_category_id':NOID,'minor_category_id':NOID,
    'quantity':integer(minimum=1),'order_id':NOID,'cart_id':NOID,'search_query':string(200,True),
    'source':string(100,minimum=1),'recommendation_id':string(128,True),'event_at':DATE,
    'score_version':integer(minimum=1),'processed_at':NDATE,'metadata':typ('object')},updated=False)
rule('behavior_events',{'$or':[{'$ne':['$user_id',None]},{'$ne':['$anonymous_id',None]}]})
rule('behavior_events',implies({'$eq':['$event_type','PURCHASE']},{'$and':[
    {'$ne':['$user_id',None]},{'$ne':['$order_id',None]},{'$ne':['$product_id',None]}]}))
rule('behavior_events',implies({'$in':['$event_type',['ADD_TO_CART','PRODUCT_VIEW']]},{'$ne':['$product_id',None]}))
rule('behavior_events',implies({'$eq':['$event_type','SEARCH']},{'$and':[
    {'$ne':['$search_query',None]},{'$ne':['$search_query','']}]}))
rule('behavior_events',{'$lte':[{'$bsonSize':'$metadata'},2048]})

def scores(cap=None):
    return {'bsonType':'object','additionalProperties':obj({'raw_score':num(),'score':num(maximum=cap),'last_event_at':DATE})}
document('user_preference_scores',{'user_id':OID,'score_version':integer(minimum=1),
    'major_categories':scores(70),'minor_categories':scores(30),'products':scores(),
    'cross_category_scores':scores(),'last_processed_event_at':NDATE},created=False)

document('product_repurchase_stats',{'product_id':OID,'major_category_id':OID,'minor_category_id':OID,
    'period_type':enum('12m'),'period_start':DATE,'period_end':DATE,'unique_buyer_count':integer(),
    'repeat_customer_count':integer(),'order_count':integer(),'repeat_purchase_rate':num(True,0,1),
    'avg_purchase_frequency':num(True),'median_repurchase_interval_days':num(True),
    'p25_repurchase_interval_days':num(True),'p75_repurchase_interval_days':num(True),
    'sample_size_status':enum('insufficient','adequate'),'calculated_at':DATE},created=False,updated=False)
rule('product_repurchase_stats',{'$lt':['$period_start','$period_end']})
rule('product_repurchase_stats',{'$lte':['$repeat_customer_count','$unique_buyer_count']})
rule('product_repurchase_stats',{'$cond':[{'$eq':['$unique_buyer_count',0]},
    {'$and':[{'$eq':['$repeat_purchase_rate',None]},{'$eq':['$avg_purchase_frequency',None]}]},
    {'$and':[{'$eq':['$repeat_purchase_rate',{'$divide':['$repeat_customer_count','$unique_buyer_count']}]},
             {'$eq':['$avg_purchase_frequency',{'$divide':['$order_count','$unique_buyer_count']}]}]}]})

pair=obj({'major_category_id':OID,'minor_category_id':OID})
document('cross_category_rules',{'antecedent':pair,'consequent':pair,'window_days':integer(minimum=1),
    'support':RATE,'confidence':RATE,'lift':num(),'co_purchase_count':integer(),
    'antecedent_customer_count':integer(),'rule_score':num(),'minimum_sample_size':integer(minimum=1),
    'source':enum('historical_transactions'),'status':ACTIVE,'calculated_at':DATE},created=False,updated=False)
rule('cross_category_rules',{'$lte':['$co_purchase_count','$antecedent_customer_count']})
document('product_purchase_sequences',{'user_id':OID,'first_product_id':OID,'next_product_id':OID,
    'first_order_id':OID,'next_order_id':OID,'days_between':integer(),'window_days':integer(minimum=1),
    'first_major_category_id':OID,'next_major_category_id':OID},updated=False)
rule('product_purchase_sequences',{'$lte':['$days_between','$window_days']})

document('recommendation_pools',{'pool_type':enum('FIRST_MEMBER'),'major_category_id':OID,
    'product_ids':arr(OID,unique=True),'filters':obj({'rating_status':enum('ACTUAL'),
        'average_rating_display_gte':num(minimum=4.5,maximum=5),'status':enum('active'),'is_ai_recommendable':enum(True)}),
    'generated_at':DATE,'expires_at':DATE},created=False,updated=False)
rule('recommendation_pools',{'$lt':['$generated_at','$expires_at']})
document('first_member_recommendations',{'user_id':OID,'recommendation_session_id':string(128,minimum=1),
    'recommendation_type':enum('FIRST_MEMBER'),'items':arr(obj({'major_category_id':OID,'product_id':OID,
        'average_rating_display':num(minimum=4.5,maximum=5),'rating_count':integer(minimum=1),'position':integer(minimum=1)})),
    'rule_version':integer(minimum=1),'random_seed':string(128,minimum=1)},updated=False)
rule('first_member_recommendations',unique_items('$items.major_category_id'))
rule('first_member_recommendations',unique_items('$items.product_id'))
document('recommendation_logs',{'user_id':OID,'recommendation_id':string(128,minimum=1),
    'recommendation_type':enum('PERSONALIZED','CROSS_CATEGORY','FIRST_MEMBER'),'algorithm_version':CODE,
    'items':arr(obj({'product_id':OID,'position':integer(minimum=1),'score':num(),'reason_code':CODE})),
    'shown_at':DATE,'clicked_product_ids':arr(OID,unique=True),'added_to_cart_product_ids':arr(OID,unique=True),
    'purchased_product_ids':arr(OID,unique=True)},updated=False)
rule('recommendation_logs',unique_items('$items.product_id'))
for name in ('first_member_recommendations','recommendation_logs'):
    rule(name,{'$eq':['$items.position',{'$range':[1,{'$add':[{'$size':'$items'},1]}]}]})
for kind,size in [('PERSONALIZED',6),('CROSS_CATEGORY',4)]:
    rule('recommendation_logs',implies({'$eq':['$recommendation_type',kind]},{'$lte':[{'$size':'$items'},size]}))
for field in ('clicked_product_ids','added_to_cart_product_ids','purchased_product_ids'):
    rule('recommendation_logs',{'$setIsSubset':['$'+field,'$items.product_id']})

SETTINGS=obj({'weights':obj({k:integer() for k in ('PURCHASE','ADD_TO_CART','SEARCH','PRODUCT_VIEW')}),
    'half_life_days':obj({k:integer(minimum=1) for k in ('PURCHASE','ADD_TO_CART','SEARCH','PRODUCT_VIEW')}),
    'major_score_cap':typ('int',enum=[70]),'minor_score_cap':typ('int',enum=[30]),
    'personalized_count':typ('int',enum=[6]),'cross_category_count':typ('int',enum=[4]),
    'first_member_min_rating':num(minimum=4.5,maximum=5),'default_product_rating':num(minimum=4,maximum=4),
    'cross_min_customers':integer(minimum=1),'cross_min_co_purchases':integer(minimum=1),
    'cross_min_confidence':RATE,'cross_min_lift':num(minimum=1)})
document('system_configs',{'config_key':enum('recommendation_policy'),'version':integer(minimum=1),
    'settings':SETTINGS,'status':ACTIVE})

for name in CORE: INDEXES[name]=[]
def idx(name,fields,unique=False,partial=None):
    keys=[(f,1) for f in fields.split()] if isinstance(fields,str) else fields
    label=('uq_' if unique else 'idx_')+name+'_'+'_'.join(k.replace('.','_') for k,v in keys)
    if partial: label+='_active'
    options={'name':label}
    if unique: options['unique']=True
    if partial: options['partialFilterExpression']=partial
    INDEXES[name].append(IndexModel(keys,**options))

idx('users','email',True); idx('users','registered_at')
# Keep null-safe firebase identity protection even though local is the current auth mode.
INDEXES['users'].append(deepcopy(next(i for i in PREVIOUS_INDEXES['users'] if i.document['name']=='uq_users_firebase_uid')))
idx('categories','category_code',True); idx('categories','parent_id status sort_order')
idx('brands','brand_code',True); idx('brands','name')
idx('products','product_code',True);idx('products','major_category_id minor_category_id status')
idx('products',[('status',1),('average_rating_display',-1)])
idx('products','is_ai_recommendable status major_category_id')
idx('product_skus','sku_code',True);idx('product_skus','product_id status')
idx('product_reviews','user_id order_item_id',True);idx('product_reviews','product_id status')
idx('orders','order_number',True);idx('orders','user_id checkout_id',True)
idx('orders',[('user_id',1),('ordered_at',-1)]);idx('orders',[('status',1),('ordered_at',-1)])
idx('orders',[('is_demo',1),('payment_status',1),('ordered_at',-1)])
idx('order_items',[('product_id',1),('created_at',-1)]);idx('order_items',[('user_id',1),('created_at',-1)])
idx('order_items','order_id');idx('order_items','order_id sku_id',True)
INDEXES['carts']=deepcopy(PREVIOUS_INDEXES['carts'])
INDEXES['cart_events']=deepcopy(PREVIOUS_INDEXES['cart_events']);idx('cart_events','event_id',True)
idx('behavior_events','event_id',True)
idx('behavior_events',[('user_id',1),('event_at',-1)])
idx('behavior_events',[('user_id',1),('event_type',1),('event_at',-1)])
idx('behavior_events',[('product_id',1),('event_at',-1)])
idx('behavior_events',[('processed_at',1),('event_at',1)])
idx('user_preference_scores','user_id',True)
idx('product_repurchase_stats','product_id period_type period_start period_end',True)
idx('cross_category_rules','antecedent.major_category_id status')
idx('cross_category_rules',[('antecedent.minor_category_id',1),('confidence',-1),('lift',-1)])
idx('product_purchase_sequences','user_id first_order_id next_order_id first_product_id next_product_id',True)
idx('recommendation_pools','pool_type major_category_id',True)
idx('first_member_recommendations','user_id',True)
idx('recommendation_logs','recommendation_id',True);idx('recommendation_logs',[('user_id',1),('shown_at',-1)])
idx('system_configs','config_key',True)


def default_policy():
    now=datetime.now(timezone.utc)
    return {'schema_version':4,'config_key':'recommendation_policy','version':1,'status':'active',
        'created_at':now,'updated_at':now,'settings':{
            'weights':{'PURCHASE':4,'ADD_TO_CART':3,'SEARCH':2,'PRODUCT_VIEW':1},
            'half_life_days':{'PURCHASE':365,'ADD_TO_CART':180,'SEARCH':90,'PRODUCT_VIEW':30},
            'major_score_cap':70,'minor_score_cap':30,'personalized_count':6,'cross_category_count':4,
            'first_member_min_rating':4.5,'default_product_rating':4.0,'cross_min_customers':500,
            'cross_min_co_purchases':50,'cross_min_confidence':0.05,'cross_min_lift':1.2}}


def verify_complete(db):
    result=[]
    for name,validator in SCHEMAS.items():
        options=db[name].options()
        if options.get('validator')!=validator or options.get('validationLevel')!='strict' or options.get('validationAction')!='error':
            raise RuntimeError('Validator mismatch: '+name)
        actual={i['name']:i for i in db[name].list_indexes()}
        if set(actual)!={'_id_'}|{m.document['name'] for m in INDEXES[name]}:
            raise RuntimeError('Index names mismatch: '+name)
        for model in INDEXES[name]:
            expected=model.document; found=actual[expected['name']]
            for field,v in expected.items():
                if field=='key' and 'text' in v.values():
                    if found.get('weights')!={'name':1,'description':1}: raise RuntimeError('Text mismatch')
                elif found.get(field)!=v: raise RuntimeError('Index options mismatch: '+name+'/'+field)
            for f in ('unique','partialFilterExpression','expireAfterSeconds','sparse'):
                if found.get(f)!=expected.get(f): raise RuntimeError('Unexpected index option: '+name+'/'+f)
        total=db[name].count_documents({}); valid=db[name].count_documents(validator)
        if total!=valid: raise RuntimeError('Invalid existing documents: '+name)
        result.append({'collection':name,'count':total,'conforming_documents':valid,'options':options,'indexes':list(actual.values())})
    return result
