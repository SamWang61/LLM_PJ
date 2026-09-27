"""Current schema contract, audited against integration v1.1 and cart update v1.0.

Earlier migration modules are immutable. This overlay adds missing conditional
validation without changing document layout or introducing fabricated defaults.
"""
from copy import deepcopy
from bson import Decimal128
from cart_schema import SCHEMAS as PREVIOUS_SCHEMAS, INDEXES
from bootstrap_schema import two_decimals

SCHEMAS=deepcopy(PREVIOUS_SCHEMAS)


def rule(collection, expression):
    SCHEMAS[collection].setdefault('$and',[]).append({'$expr':expression})


def implies(condition, consequence):
    return {'$or':[{'$not':[condition]},consequence]}


def nonempty(field):
    return {'$and':[{'$ne':[field,None]},{'$ne':[field,'']}]}


for field in ('budget_min','budget_max'):
    rule('users',two_decimals('$preferences.'+field,True))
rule('user_events',implies({'$eq':['$event_type','recommendation_click']},
                           {'$ne':['$product_id',None]}))

# Missing cost remains null. Decimal128 Infinity is not a valid estimated bill.
rule('ai_requests',{'$or':[{'$eq':['$estimated_cost',None]},
    {'$lte':['$estimated_cost',Decimal128('9.999999999999999999999999999999999E+6144')]}]})
rule('ai_requests',implies({'$eq':['$status','running']},{'$ne':['$started_at',None]}))
rule('ai_requests',implies({'$eq':['$status','succeeded']},{'$and':[
    {'$ne':['$started_at',None]},{'$ne':['$actual_provider',None]}]}))
# Only require model provenance when a model actually executed. A failed request
# before provider selection and queued work may legitimately retain nulls.
model_executed={'$and':[{'$ne':['$started_at',None]},
                        {'$in':['$actual_provider',['huggingface','anthropic']]}]}
rule('ai_requests',implies(model_executed,{'$and':[
    nonempty('$model_name'),nonempty('$model_revision')]}))
generation={'$and':[{'$eq':['$task_type','sales_summary']},
                     {'$eq':['$actual_provider','anthropic']},{'$ne':['$started_at',None]}]}
rule('ai_requests',implies(generation,{'$and':[nonempty('$prompt_name'),nonempty('$prompt_version')]}))
rule('recommendations',implies({'$in':['$strategy',['bge_similar','bge_personalized']]},
                              {'$and':[nonempty('$model'),nonempty('$revision')]}))


def verify_current(db):
    """Check definitions and all current documents, returning no business data."""
    names=set(db.list_collection_names())
    missing=set(SCHEMAS)-names
    if missing:
        raise RuntimeError('Missing collections: '+', '.join(sorted(missing)))
    report=[]
    for name,validator in SCHEMAS.items():
        options=db[name].options()
        if options.get('validator')!=validator or options.get('validationLevel')!='strict' or options.get('validationAction')!='error':
            raise RuntimeError('Validator mismatch: '+name)
        actual={i['name']:i for i in db[name].list_indexes()}
        expected_names={'_id_'} | {i.document['name'] for i in INDEXES[name]}
        if set(actual)!=expected_names:
            raise RuntimeError('Index name mismatch: '+name)
        for model in INDEXES[name]:
            expected=model.document
            found=actual[expected['name']]
            for field,value in expected.items():
                if field=='key' and 'text' in value.values():
                    if found.get('weights')!={'name':1,'description':1}:
                        raise RuntimeError('Text weights mismatch')
                elif found.get(field)!=value:
                    raise RuntimeError('Index mismatch: '+name+'/'+expected['name']+'/'+field)
            if bool(found.get('unique',False))!=bool(expected.get('unique',False)):
                raise RuntimeError('Unique option mismatch: '+name)
            for field in ('partialFilterExpression','expireAfterSeconds','sparse'):
                if found.get(field)!=expected.get(field):
                    raise RuntimeError('Unexpected index option: '+name+'/'+field)
        count=db[name].count_documents({})
        valid=db[name].count_documents(validator)
        if count!=valid:
            raise RuntimeError(f'Noncompliant existing documents: {name} ({count-valid})')
        report.append({'collection':name,'count':count,'conforming_documents':valid,
                       'options':options,'indexes':list(actual.values())})
    return report
