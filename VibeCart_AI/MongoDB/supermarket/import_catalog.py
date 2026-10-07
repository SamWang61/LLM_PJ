"""Add classroom products to existing v4 schema without resetting live stock.

Default: validate writes in an aborted transaction. --apply commits insert-only
upserts. Credentials are loaded from the existing ignored MongoDB/.env file.
"""
import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from bson import ObjectId, Decimal128, json_util
from pymongo import UpdateOne

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from bootstrap_schema import connect
from schema_complete_v4 import SCHEMAS

BATCH = 'supermarket-carrefour-20261005'
USE = {
    'DAIRY': '早餐搭配與家庭日常採買', 'FROZEN': '家庭備餐與冷凍食品選購',
    'DRINK': '日常飲用與聚會補給', 'SNACK': '點心分享與零食採買',
    'GROCERY': '家庭主食準備與烹調採買', 'PANTRY': '料理調味與日常沖泡',
    'HOME': '居家清潔與日用品補貨', 'CARE': '日常清潔與個人用品補貨',
}


def oid(kind, key):
    return ObjectId(hashlib.sha256(f'{BATCH}:{kind}:{key}'.encode()).hexdigest()[:24])


def build(source):
    rows = source['items']
    assert len(rows) >= 300 and len({r['source_id'] for r in rows}) == len(rows)
    now = datetime.fromisoformat(source['collected_at'])
    docs = {n: [] for n in ('categories', 'brands', 'products', 'product_skus')}
    majors, minors, brands = {}, {}, {}
    for index, r in enumerate(rows):
        assert r['image_http_status'] == 200 and r['specification']
        assert '\ufffd' not in r['name'] and len(r['name']) <= 200
        major, minor = 'SM-' + r['major_code'], 'SM-' + r['minor_code']
        major_id, minor_id = oid('category', major), oid('category', minor)
        if major not in majors:
            majors[major] = {'_id': major_id, 'schema_version': 4, 'category_code': major,
                'name': r['major_category'], 'level': 1, 'parent_id': None, 'path': [major],
                'status': 'active', 'sort_order': len(majors), 'created_at': now, 'updated_at': now}
        if minor not in minors:
            minors[minor] = {'_id': minor_id, 'schema_version': 4, 'category_code': minor,
                'name': r['minor_category'], 'level': 2, 'parent_id': major_id, 'path': [major, minor],
                'status': 'active', 'sort_order': len(minors), 'created_at': now, 'updated_at': now}
        brand_id = None
        if r.get('brand'):
            brand = r['brand']
            brand_id = oid('brand', brand)
            brands[brand] = {'_id': brand_id, 'schema_version': 4,
                'brand_code': 'CFB-' + hashlib.sha256(brand.encode()).hexdigest()[:16],
                'name': brand, 'description': '公開商品頁列示的品牌名稱。',
                'status': 'active', 'created_at': now, 'updated_at': now}
        pid = oid('product', r['source_id'])
        summary = f"{r['name']}，來源規格為 {r['specification']}。歸入{r['major_category']}／{r['minor_category']}，供{USE[r['major_code']]}情境測試。"
        description = (summary + '\n教學測試商品：描述為自行改寫，價格為擷取時的參考值，庫存為模擬值；不提供實際出貨。'
                       + '\n規格、成分、保存及使用方式請以來源頁與商品包裝為準。'
                       + '\n商品來源：' + r['source_url'])
        docs['products'].append({'_id': pid, 'schema_version': 4, 'product_code': 'CF-' + r['source_id'],
            'product_name': r['name'], 'product_aliases': [], 'brand_id': brand_id,
            'major_category_id': major_id, 'minor_category_id': minor_id, 'category_path': [major, minor],
            'summary': summary, 'description': description, 'usage_scenarios': [USE[r['major_code']]],
            'target_segments': ['超市購物測試使用者'],
            'product_tags': ['教學測試', r['major_category'], r['minor_category']],
            'status': 'active', 'is_ai_recommendable': True, 'image_urls': [r['image_url']],
            'shipping_profile_id': None, 'rating_status': 'DEFAULT', 'rating_default_value': 4.0,
            'rating_sum': 0, 'rating_count': 0, 'average_rating_raw': None, 'average_rating_display': 4.0,
            'rating_distribution': {f'star_{i}': 0 for i in range(1, 6)},
            'product_lifecycle_type': 'consumable', 'replenishment_enabled': False,
            'expected_repurchase_interval_days': None, 'expected_purchase_frequency_year': None,
            'minimum_repeat_frequency_year': 0.0, 'replenishment_basis': 'category_benchmark',
            'replenishment_confidence': 0.0, 'repeat_purchase_rate_12m': None,
            'repeat_customer_count_12m': 0, 'unique_buyer_count_12m': 0, 'order_count_12m': 0,
            'avg_purchase_frequency_12m': None, 'median_repurchase_interval_days': None,
            'last_repurchase_calculated_at': None, 'created_at': now, 'updated_at': now})
        # Known demo cases, never represented as retailer inventory.
        stock = 0 if index % 29 == 0 else (3 if index % 11 == 0 else 40 + index % 61)
        docs['product_skus'].append({'_id': oid('sku', r['source_id']), 'schema_version': 4,
            'product_id': pid, 'sku_code': 'CF-SKU-' + r['source_id'],
            'variant_attributes': {'規格': r['specification']},
            'price': Decimal128(Decimal(r['source_price_twd']).quantize(Decimal('0.01'))),
            'cost_price': None, 'currency': 'TWD', 'stock_quantity': stock, 'reserved_quantity': 0,
            'available_quantity': stock, 'safety_stock': 10,
            'stock_status': 'out_of_stock' if stock == 0 else ('low_stock' if stock <= 10 else 'in_stock'),
            'barcode': None, 'weight_grams': None, 'status': 'active', 'created_at': now, 'updated_at': now})
    docs['categories'] = [*majors.values(), *minors.values()]
    docs['brands'] = list(brands.values())
    return docs


def check_references(docs):
    categories = {d['_id']: d for d in docs['categories']}
    products = {d['_id']: d for d in docs['products']}
    for p in products.values():
        assert categories[p['major_category_id']]['level'] == 1
        assert categories[p['minor_category_id']]['parent_id'] == p['major_category_id']
    assert len(docs['product_skus']) == len(products)
    for sku in docs['product_skus']:
        assert sku['product_id'] in products
        assert sku['price'].to_decimal() > 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    source_bytes = (ROOT / 'source_catalog.json').read_bytes()
    source = json.loads(source_bytes)
    docs = build(source)
    check_references(docs)
    (ROOT / 'catalog_v4.extjson').write_text(json_util.dumps(docs, ensure_ascii=False, indent=2), encoding='utf-8')
    with (ROOT / 'catalog_preview.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = ['source_id', 'name', 'major_category', 'minor_category', 'specification', 'source_price_twd', 'source_url', 'image_url']
        writer = csv.DictWriter(f, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(source['items'])
    with connect('.env') as client:
        db = client.vibecart_ai
        before = {n: db[n].count_documents({}) for n in docs}
        before_total = {n: db[n].count_documents({}) for n in db.list_collection_names()}
        for name in docs:
            options = db[name].options()
            assert options.get('validator') == SCHEMAS[name], 'Schema drift: ' + name
            assert options.get('validationLevel') == 'strict' and options.get('validationAction') == 'error'
            identity = {'categories': 'category_code', 'brands': 'brand_code', 'products': 'product_code', 'product_skus': 'sku_code'}[name]
            rows = list(db[name].find({'$or': [
                {'_id': {'$in': [d['_id'] for d in docs[name]]}},
                {identity: {'$in': [d[identity] for d in docs[name]]}}]}))
            by_id = {d['_id']: d for d in rows}
            by_code = {d[identity]: d for d in rows}
            for doc in docs[name]:
                for existing in (by_id.get(doc['_id']), by_code.get(doc[identity])):
                    if existing:
                        assert existing['_id'] == doc['_id'] and existing[identity] == doc[identity], 'Identity collision'
                        if name == 'product_skus':
                            assert existing['product_id'] == doc['product_id'], 'SKU owner mismatch'
        def write(session):
            inserted = {}
            for name, values in docs.items():
                if values:
                    result = db[name].bulk_write([UpdateOne({'_id': d['_id']}, {'$setOnInsert': d}, upsert=True) for d in values], session=session)
                    inserted[name] = result.upserted_count
                else:
                    inserted[name] = 0
            return inserted
        with client.start_session() as session:
            if args.apply:
                inserted = session.with_transaction(write)
            else:
                session.start_transaction()
                try:
                    inserted = write(session)
                finally:
                    session.abort_transaction()
        after = {n: db[n].count_documents({}) for n in docs}
        for n, count in before_total.items():
            if n not in docs:
                assert db[n].count_documents({}) == count, 'Unrelated collection changed: ' + n
        if not args.apply:
            assert before == after
        else:
            for n, values in docs.items():
                ids = [d['_id'] for d in values]
                assert db[n].count_documents({'_id': {'$in': ids}}) == len(ids)
                assert db[n].count_documents({'$and': [{'_id': {'$in': ids}}, SCHEMAS[n]]}) == len(ids)
        report = {'batch': BATCH, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'database': 'vibecart_ai', 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            'mode': 'applied' if args.apply else 'validated_and_aborted', 'before': before,
            'inserted' if args.apply else 'would_insert': inserted, 'after': after,
            'policy': 'insert-only; rerun does not reset stock, ratings, prices or user edits',
            'source_product_count': len(source['items']), 'images_verified': len(source['items']),
            'major_categories': len({r['major_code'] for r in source['items']}),
            'minor_categories': len({r['minor_code'] for r in source['items']})}
        filename = 'import_report.json' if args.apply else 'validation_report.json'
        (ROOT / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
