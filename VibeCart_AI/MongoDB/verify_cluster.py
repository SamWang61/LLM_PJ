"""Database integration checks; test writes are isolated in aborted transactions."""
from copy import deepcopy
from datetime import datetime, timezone
import math
import uuid
from bson import ObjectId, Decimal128
from pymongo.errors import OperationFailure
from bootstrap_schema import ROOT, connect, verify


def main():
    results = []
    now = datetime.now(timezone.utc)
    prefix = 'verify-' + uuid.uuid4().hex
    uid, pid, cid = ObjectId(), ObjectId(), ObjectId()
    common = {'schema_version': 2, 'created_at': now, 'updated_at': now}
    category = {**common, '_id':cid, 'name':prefix, 'slug':prefix,
                'description':None, 'sort_order':0, 'is_active':True}
    user = {**common, '_id':uid, 'display_name':'Database verification',
            'email':prefix+'@example.invalid', 'auth_provider':'local',
            'password_hash':'test-only-not-a-login-account', 'firebase_uid':None,
            'role':'customer', 'is_active':True, 'preferences':{'category_ids':[],
            'tags':[], 'budget_min':None, 'budget_max':None, 'updated_at':None}}
    product = {**common, '_id':pid, 'category_id':cid, 'name':prefix, 'description':'temporary verification',
               'sku':prefix.upper(), 'brand':None, 'size':None, 'color':None,
               'price':Decimal128('0.10'), 'sale_price':None, 'currency':'TWD',
               'stock_quantity':1, 'safety_stock':0, 'tags':[], 'image_urls':[], 'is_active':True}
    order = {**common, '_id':ObjectId(), 'order_number':prefix, 'user_id':uid,
             'checkout_id':prefix, 'request_hash':'0'*64, 'status':'confirmed',
             'payment_status':'paid', 'is_demo':True, 'currency':'TWD',
             'items':[{'product_id':pid, 'product_name':prefix, 'sku':prefix.upper(),
                       'size':None, 'color':None, 'unit_price':Decimal128('0.10'),
                       'quantity':3, 'subtotal_amount':Decimal128('0.30')}],
             'subtotal_amount':Decimal128('0.30'), 'discount_amount':Decimal128('0'),
             'shipping_fee':Decimal128('0'), 'total_amount':Decimal128('0.30'),
             'shipping_address':None, 'paid_at':now}
    event = {'_id':ObjectId(), 'schema_version':2, 'created_at':now, 'event_id':prefix,
             'user_id':uid, 'session_id':prefix, 'event_type':'purchase', 'product_id':None,
             'order_id':order['_id'], 'recommendation_id':None, 'search_query':None, 'event_metadata':{}}
    embedding = {**common, '_id':ObjectId(), 'product_id':pid, 'model':'BAAI/bge-small-zh-v1.5',
                 'revision':'verification-only', 'vector':[1.0]+[0.0]*511, 'dimension':512,
                 'content_hash':'0'*64, 'preprocessing_version':'verification-only', 'is_normalized':True}

    with connect('.env') as client:
        db = client.vibecart_ai
        before = {n:db[n].count_documents({}) for n in db.list_collection_names()}

        def check(label, action, expected=None):
            with client.start_session() as session:
                session.start_transaction()
                try:
                    action(session)
                    assert expected is None, 'Expected database rejection'
                except OperationFailure as exc:
                    assert exc.code == expected, (label, exc.code, expected)
                finally:
                    if session.in_transaction:
                        session.abort_transaction()
            results.append((label, 'PASS'))

        def put(collection, document):
            return lambda s: db[collection].insert_one(deepcopy(document), session=s)

        def duplicate(collection, first, change):
            def action(s):
                db[collection].insert_one(deepcopy(first), session=s)
                second = deepcopy(first)
                second.update({'_id':ObjectId(), **change})
                db[collection].insert_one(second, session=s)
            return action

        check('Application account connects and inserts valid schema v2', put('users', user))
        check('Duplicate email rejected', duplicate('users', user, {}), 11000)
        check('Multiple null firebase_uid accepted', duplicate('users', user, {'email':'second-'+user['email']}))
        check('Duplicate SKU rejected', duplicate('products', product, {}), 11000)
        check('Duplicate checkout key rejected', duplicate('orders', order, {'order_number':prefix+'-second'}), 11000)
        check('Duplicate purchase order rejected', duplicate('user_events', event, {'event_id':prefix+'-second'}), 11000)
        check('Money stored as double rejected', put('products', {**product, 'price':0.1}), 121)
        check('Money with three decimal places rejected', put('products', {**product, 'price':Decimal128('0.123')}), 121)
        check('Sale greater than price rejected', put('products', {**product, 'sale_price':Decimal128('1')}), 121)
        check('Negative stock rejected', put('products', {**product, 'stock_quantity':-1}), 121)
        check('Incorrect order total rejected', put('orders', {**order, 'total_amount':Decimal128('0.40')}), 121)
        check('Missing purchase order_id rejected', put('user_events', {**event, 'order_id':None}), 121)
        check('Valid 512 dimension vector accepted', put('product_embeddings', embedding))
        check('Wrong vector length rejected', put('product_embeddings', {**embedding, 'vector':[1.0]}), 121)
        check('Zero vector rejected', put('product_embeddings', {**embedding, 'vector':[0.0]*512}), 121)
        check('Infinite vector rejected', put('product_embeddings', {**embedding, 'vector':[math.inf]+[0.0]*511}), 121)
        check('NaN vector rejected', put('product_embeddings', {**embedding, 'vector':[math.nan]+[0.0]*511}), 121)

        def rollback(s):
            db.categories.insert_one(deepcopy(category), session=s)
            db.products.insert_one(deepcopy(product), session=s)
            db.orders.insert_one(deepcopy(order), session=s)
            result = db.products.update_one({'_id':pid, 'stock_quantity':{'$gte':1}}, {'$inc':{'stock_quantity':-1}}, session=s)
            assert result.modified_count == 1
            result = db.products.update_one({'_id':pid, 'stock_quantity':{'$gte':1}}, {'$inc':{'stock_quantity':-1}}, session=s)
            assert result.modified_count == 0
            assert db.products.find_one({'_id':pid}, session=s)['stock_quantity'] == 0
        check('Multi-collection transaction and conditional stock update; all rolled back', rollback)
        value = list(db.aggregate([{'$documents':[{'a':Decimal128('0.10'),'b':Decimal128('0.20')}]},
                                   {'$project':{'sum':{'$add':['$a','$b']}}}]))[0]['sum']
        assert value.to_decimal() == Decimal128('0.30').to_decimal()
        results.append(('Server Decimal128 0.10 + 0.20 = 0.30', 'PASS'))
        after = {n:db[n].count_documents({}) for n in db.list_collection_names()}
        assert before == after, 'Unexpected remaining test data'
        results.append(('All verification writes rolled back; original counts preserved', 'PASS'))

    with connect() as manager:
        report = verify(manager.vibecart_ai)
        assert sum(len(x['indexes']) for x in report) == 36
        results.append(('13 strict validators / 23 custom indexes / 36 total indexes read back', 'PASS'))
    text = '# 資料庫實際驗證結果\n\n'
    text += '執行時間：' + datetime.now(timezone.utc).isoformat() + '\n\n'
    text += '使用 PyMongo 4.14.1；資料寫入測試使用 vibecart_app。所有測試交易均回滾，不保留示範會員、訂單或向量。\n\n'
    text += '|檢查|結果|\n|---|---|\n' + ''.join(f'|{a}|{b}|\n' for a,b in results)
    text += '\n這是資料庫層驗證，不是 Flask 完整結帳、兩使用者併發、AI 推薦品質、Claude 或網站部署验收。TTL 的定義已讀回，尚未等待背景清理器的實際刪除週期。\n'
    (ROOT / '06_實際驗證結果.md').write_text(text, encoding='utf-8')
    print(f'{len(results)} database checks passed; no test data retained')


if __name__ == '__main__':
    main()
