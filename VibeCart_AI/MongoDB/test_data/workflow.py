"""Deterministic synthetic customers/orders; default generate, explicit DB actions.

Uses the existing private connection helper. Never prints credentials, modifies
products/stock, deletes data or bypasses validation. All generated orders are demo.
"""
import argparse
import calendar
import csv
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from bson import ObjectId, Decimal128, json_util
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from bootstrap_schema import connect
from schema_test_profile import SCHEMAS, BASE, CHANGED, MIGRATION, verify

BATCH = 'sam-synthetic-20261005-v1'
SEED = 20261005
TZ = timezone(timedelta(hours=8))
UTC = timezone.utc
AS_OF = date(2026, 10, 5)
AT = datetime(2026, 10, 5, 8, tzinfo=TZ).astimezone(UTC)
GROUPS = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 79)]
MARITAL = ['single', 'married', 'divorced', 'widowed', 'unspecified']
OUT = HERE / 'generated'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS,
                           sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def save(path, value):
    path.write_text(json_util.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load(path):
    return json_util.loads(path.read_text(encoding='utf-8'), json_options=json_util.JSONOptions(tz_aware=True))


def oid(kind, key):
    return ObjectId(hashlib.sha256(f'{BATCH}:{kind}:{key}'.encode()).hexdigest()[:24])


def money(value):
    return Decimal128(Decimal(value).quantize(Decimal('0.01')))


def age(born, reference=AS_OF):
    return reference.year - born.year - ((reference.month, reference.day) < (born.month, born.day))


def catalog_snapshot(db):
    products = list(db.products.find({}).sort('_id', 1))
    skus = list(db.product_skus.find({}).sort('_id', 1))
    require(products and skus, 'Catalog is empty')
    return {'products': products, 'product_skus': skus}


def build(catalog):
    rng = random.Random(SEED)
    products = {p['_id']: p for p in catalog['products']}
    skus = [s for s in catalog['product_skus'] if s['status'] == 'active'
            and products[s['product_id']]['status'] == 'active']
    require(len(skus) >= 5, 'Need at least five valid SKU references')
    docs = {n: [] for n in CHANGED}
    for g, (lo, hi) in enumerate(GROUPS):
        for gender in ('male', 'female'):
            for marital in MARITAL:
                for repeat in range(10):
                    i = len(docs['users'])
                    years = rng.randint(lo, hi)
                    # Dates are real calendar dates and ages are defined at AS_OF.
                    born = date(AS_OF.year - years, rng.randint(1, 12), rng.randint(1, 28))
                    if age(born) < years:
                        born = born.replace(year=born.year - 1)
                    adulthood = born.replace(year=born.year + 18)
                    registered = datetime.combine(max(date(2023, 1, 1), adulthood), datetime.min.time(), TZ).astimezone(UTC)
                    docs['users'].append({
                        '_id': oid('user', i), 'schema_version': 4,
                        'display_name': f'測試會員{i+1:04d}', 'email': f'sam-test-{i+1:04d}@example.com',
                        'auth_provider': 'local', 'password_hash': '!synthetic-login-disabled',
                        'firebase_uid': None, 'role': 'customer', 'is_active': False, 'status': 'inactive',
                        'preferences': {'category_ids': [], 'tags': [], 'budget_min': None,
                                        'budget_max': None, 'updated_at': None},
                        'member_level': ['normal', 'silver', 'gold'][i % 3],
                        'registered_at': registered, 'first_recommendation_generated_at': None,
                        'last_login_at': None, 'created_at': registered, 'updated_at': AT,
                        'synthetic_batch_id': BATCH,
                        'demographics': {'gender': gender, 'birth_date': born.isoformat(),
                                         'marital_status': marital, 'as_of_date': AS_OF.isoformat()},
                    })
    start = datetime(2024, 1, 1, tzinfo=TZ)
    end = datetime(2026, 10, 5, tzinfo=TZ)
    boundary = [start, datetime(2024, 2, 29, 12, tzinfo=TZ),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=TZ), datetime(2025, 1, 1, tzinfo=TZ),
                datetime(2025, 12, 31, 23, 59, 59, tzinfo=TZ), datetime(2026, 1, 1, tzinfo=TZ), end]
    times = boundary + [start + timedelta(seconds=rng.randrange(int((end-start).total_seconds())))
                        for _ in range(3000-len(boundary))]
    for i, when in enumerate(sorted(times)):
        when = when.astimezone(UTC)
        eligible = [u for j, u in enumerate(docs['users']) if j % 10 != 9 and u['registered_at'] <= when]
        user = rng.choice(eligible)
        selected = rng.sample(skus, rng.randint(1, 5))
        order_id = oid('order', i)
        lines = []
        for j, sku in enumerate(selected):
            p = products[sku['product_id']]
            qty = rng.randint(1, 5)
            lines.append({'_id': oid('line', f'{i}:{j}'), 'schema_version': 4,
                          'order_id': order_id, 'user_id': user['_id'], 'product_id': p['_id'],
                          'sku_id': sku['_id'], 'product_code_snapshot': p['product_code'],
                          'product_name_snapshot': p['product_name'],
                          'major_category_id_snapshot': p['major_category_id'],
                          'minor_category_id_snapshot': p['minor_category_id'],
                          'quantity': qty, 'unit_price': sku['price'],
                          'line_total': money(sku['price'].to_decimal()*qty),
                          'created_at': when, 'synthetic_batch_id': BATCH})
        subtotal = sum((line['line_total'].to_decimal() for line in lines), Decimal(0))
        discount = (subtotal * Decimal('0.10')).quantize(Decimal('0.01')) if i % 10 == 0 else Decimal(0)
        fee = Decimal(0) if subtotal-discount >= 1500 else Decimal(80)
        status, payment, shipping = [
            ('completed', 'paid', 'delivered'), ('completed', 'paid', 'delivered'),
            ('completed', 'paid', 'delivered'), ('completed', 'paid', 'delivered'),
            ('shipping', 'paid', 'shipped'), ('confirmed', 'paid', 'processing'),
            ('pending', 'unpaid', 'pending'), ('pending', 'failed', 'pending'),
            ('cancelled', 'refunded', 'returned'), ('cancelled', 'unpaid', 'cancelled')][i % 10]
        paid_at = min(when+timedelta(minutes=10), AT) if payment in ('paid', 'refunded') else None
        completed_at = min(when+timedelta(days=2), AT) if status == 'completed' else None
        docs['orders'].append({'_id': order_id, 'schema_version': 4, 'user_id': user['_id'],
            'order_number': f'SAMTEST-20261005-{i+1:05d}', 'status': status,
            'payment_status': payment, 'shipping_status': shipping, 'subtotal': money(subtotal),
            'shipping_fee': money(fee), 'total_amount': money(subtotal-discount+fee),
            'ordered_at': when, 'completed_at': completed_at, 'checkout_id': f'{BATCH}-{i}',
            'request_hash': digest([{'sku': l['sku_id'], 'quantity': l['quantity']} for l in lines]),
            'is_demo': True, 'currency': 'TWD', 'paid_at': paid_at, 'discount_amount': money(discount),
            'created_at': when, 'updated_at': max(when, paid_at or when, completed_at or when),
            'synthetic_batch_id': BATCH})
        docs['order_items'].extend(lines)
    validate(docs, catalog)
    return docs


def validate(docs, catalog):
    users = {u['_id']: u for u in docs['users']}
    products = {p['_id']: p for p in catalog['products']}
    skus = {s['_id']: s for s in catalog['product_skus']}
    orders = {o['_id']: o for o in docs['orders']}
    sums, keys = defaultdict(Decimal), set()
    for name, rows in docs.items():
        require(len({r['_id'] for r in rows}) == len(rows), 'Duplicate IDs: '+name)
        require(all(r['synthetic_batch_id'] == BATCH for r in rows), 'Batch mismatch')
    require(len(users) == 600 and len(orders) == 3000, 'Unexpected counts')
    for u in users.values():
        d = u['demographics']; born = date.fromisoformat(d['birth_date'])
        require(18 <= age(born) <= 79 and u['role'] == 'customer' and not u['is_active'], 'Invalid test profile')
    for line in docs['order_items']:
        o = orders[line['order_id']]; sku = skus[line['sku_id']]; p = products[line['product_id']]
        require(line['user_id'] == o['user_id'] and sku['product_id'] == p['_id'], 'Reference mismatch')
        require((o['_id'], sku['_id']) not in keys, 'Duplicate SKU per order')
        keys.add((o['_id'], sku['_id']))
        require(line['line_total'].to_decimal() == line['unit_price'].to_decimal()*line['quantity'], 'Line math')
        require(line['major_category_id_snapshot'] == p['major_category_id'] and
                line['minor_category_id_snapshot'] == p['minor_category_id'], 'Category mismatch')
        sums[o['_id']] += line['line_total'].to_decimal()
    for o in orders.values():
        u = users[o['user_id']]
        require(u['registered_at'] <= o['ordered_at'] <= AT, 'Order chronology')
        require(age(date.fromisoformat(u['demographics']['birth_date']), o['ordered_at'].astimezone(TZ).date()) >= 18, 'Minor order')
        require(o['is_demo'] is True, 'Synthetic order must be demo')
        require(sums[o['_id']] == o['subtotal'].to_decimal(), 'Subtotal mismatch')
        require(o['total_amount'].to_decimal() == sums[o['_id']] - o['discount_amount'].to_decimal() + o['shipping_fee'].to_decimal(), 'Total mismatch')
        for field in ('paid_at', 'completed_at'):
            require(o[field] is None or o['ordered_at'] <= o[field] <= AT, 'Status chronology')
    require(len(set(users)-{o['user_id'] for o in orders.values()}) >= 60, 'Missing zero-order cohort')


def expected(docs):
    monthly = {}
    daily = {}
    demographics = Counter()
    top = Counter()
    valid_ids = set()
    for u in docs['users']:
        d = u['demographics']; years = age(date.fromisoformat(d['birth_date']))
        group = next(f'{lo}-{hi}' for lo, hi in GROUPS if lo <= years <= hi)
        demographics[(d['gender'], group, d['marital_status'])] += 1
    for o in docs['orders']:
        day = o['ordered_at'].astimezone(TZ).date().isoformat()
        for groups, key in ((monthly, day[:7]), (daily, day)):
            row = groups.setdefault(key, {'orders': 0, 'valid_orders': 0, 'revenue': Decimal(0)})
            row['orders'] += 1
            if o['payment_status'] == 'paid' and o['status'] != 'cancelled':
                row['valid_orders'] += 1; row['revenue'] += o['total_amount'].to_decimal()
                valid_ids.add(o['_id'])
    for line in docs['order_items']:
        if line['order_id'] in valid_ids:
            top[line['product_code_snapshot']] += line['quantity']
    for groups in (monthly, daily):
        for row in groups.values():
            row['average_order'] = str((row['revenue']/row['valid_orders']).quantize(Decimal('0.01'))) if row['valid_orders'] else '0.00'
            row['revenue'] = str(row['revenue'])
    return {'batch': BATCH, 'timezone': 'Asia/Taipei', 'is_demo': True,
            'monthly': monthly, 'daily': daily, 'top_products': sorted(top.items(), key=lambda p: (-p[1], p[0])),
            'demographics': [{'gender': k[0], 'age_group': k[1], 'marital_status': k[2], 'count': v}
                             for k, v in sorted(demographics.items())],
            'excluded_demo_expected_orders': 0}


def migrate(db):
    checksum = hashlib.sha256((HERE/'schema_test_profile.py').read_bytes()).hexdigest()
    record = db.schema_migrations.find_one({'_id': MIGRATION})
    if record:
        require(record['status'] == 'succeeded' and record['checksum'] == checksum, 'Migration needs manual review')
        return verify(db)
    require(set(db.list_collection_names()) == set(BASE), 'Unexpected collections')
    before = {}
    for name in BASE:
        opts = db[name].options()
        require(opts.get('validator') == BASE[name] and opts.get('validationLevel') == 'strict'
                and opts.get('validationAction') == 'error', 'Baseline schema drift: '+name)
        require(db[name].count_documents({}) == db[name].count_documents(BASE[name]), 'Invalid baseline data')
        before[name] = {'options': opts, 'count': db[name].count_documents({})}
    save(OUT/'migration_before.json', before)
    db.schema_migrations.insert_one({'_id': MIGRATION, 'schema_version': 2, 'checksum': checksum,
        'status': 'running', 'started_at': datetime.now(UTC), 'completed_at': None,
        'counts': {'source': 0, 'target': 0, 'errors': 0}, 'error_code': None})
    try:
        for name in CHANGED:
            db.command('collMod', name, validator=SCHEMAS[name], validationLevel='strict', validationAction='error')
        result = verify(db)
        db.schema_migrations.update_one({'_id': MIGRATION}, {'$set': {'status': 'succeeded',
            'completed_at': datetime.now(UTC), 'counts': {'source': 3, 'target': 3, 'errors': 0}}})
        save(OUT/'migration_after.json', result)
        return result
    except Exception as exc:
        db.schema_migrations.update_one({'_id': MIGRATION}, {'$set': {'status': 'failed',
            'completed_at': datetime.now(UTC), 'error_code': type(exc).__name__}})
        raise


def run_import(db, docs, catalog, apply, verify_only=False):
    verify(db)
    require(digest(catalog_snapshot(db)) == digest(catalog), 'Catalog changed since generation')
    before = {n: db[n].count_documents({}) for n in SCHEMAS}
    missing = {}
    for name, rows in docs.items():
        existing = {r['_id']: r for r in db[name].find({'_id': {'$in': [r['_id'] for r in rows]}})}
        require(all(canonical(existing[r['_id']]) == canonical(r) for r in rows if r['_id'] in existing),
                'Existing batch data changed; will not overwrite: '+name)
        missing[name] = [r for r in rows if r['_id'] not in existing]
    if verify_only:
        require(not any(missing.values()), 'Read-only verification found missing documents')
    with db.client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority'))
        try:
            for name, rows in missing.items():
                for offset in range(0, len(rows), 1000):
                    db[name].insert_many(rows[offset:offset+1000], session=session)
            for name, rows in docs.items():
                require(db[name].count_documents({'synthetic_batch_id': BATCH}, session=session) == len(rows), 'Transaction count mismatch')
            if apply:
                session.commit_transaction()
            else:
                session.abort_transaction()
        except Exception:
            if session.in_transaction:
                session.abort_transaction()
            raise
    after = {n: db[n].count_documents({}) for n in SCHEMAS}
    for name in SCHEMAS:
        expected_delta = len(missing.get(name, [])) if apply else 0
        require(after[name] == before[name]+expected_delta, 'Concurrent count drift: '+name)
    require(digest(catalog_snapshot(db)) == digest(catalog), 'Catalog changed during import')
    report = {'batch': BATCH, 'database': 'vibecart_ai', 'checked_at': datetime.now(UTC),
              'committed': apply, 'before': before, 'after': after,
              'inserted': {n: len(v) if apply else 0 for n, v in missing.items()}, 'catalog_unchanged': True}
    if apply:
        readback = {n: list(db[n].find({'synthetic_batch_id': BATCH}).sort('_id', 1)) for n in CHANGED}
        for name in CHANGED:
            require(digest(readback[name]) == digest(sorted(docs[name], key=lambda d:d['_id'])), 'Readback differs: '+name)
        validate(readback, catalog)
        require(expected(readback) == expected(docs), 'Readback metrics differ')
        report['full_document_comparison'] = True
        report['schema_readback'] = verify(db)
        # Independent MongoDB aggregation uses the same paid/non-cancelled contract.
        actual = list(db.orders.aggregate([
            {'$match': {'synthetic_batch_id': BATCH, 'payment_status': 'paid', 'status': {'$ne': 'cancelled'}}},
            {'$group': {'_id': {'$dateToString': {'date': '$ordered_at', 'format': '%Y-%m', 'timezone': 'Asia/Taipei'}},
                        'revenue': {'$sum': '$total_amount'}, 'valid_orders': {'$sum': 1}}}]))
        for row in actual:
            e = expected(docs)['monthly'][row['_id']]
            require(row['revenue'].to_decimal() == Decimal(e['revenue']) and row['valid_orders'] == e['valid_orders'], 'Atlas monthly aggregation mismatch')
        require(len(actual) == len(expected(docs)['monthly']), 'Missing monthly aggregates')
        report['atlas_monthly_aggregation'] = 'passed'
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['generate', 'migrate', 'dry-run', 'apply', 'verify'])
    args = p.parse_args()
    OUT.mkdir(exist_ok=True)
    lock = OUT/'operation.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with connect('.env.schema' if args.action == 'migrate' else '.env') as client:
            db = client.vibecart_ai
            if args.action == 'generate':
                catalog = catalog_snapshot(db)
                docs = build(catalog)
                target = OUT/'dataset.extjson'
                require(not target.exists() or digest(load(target)) == digest(docs), 'Existing generated batch differs')
                save(OUT/'catalog_snapshot.extjson', catalog); save(target, docs)
                save(OUT/'expected_metrics.json', expected(docs))
                save(OUT/'manifest.json', {'batch': BATCH, 'seed': SEED, 'as_of': AS_OF.isoformat(),
                    'counts': {n: len(v) for n,v in docs.items()}, 'dataset_sha256': digest(docs),
                    'catalog_sha256': digest(catalog), 'all_synthetic': True, 'all_orders_demo': True})
                for name in ('users', 'orders'):
                    with (OUT/(name+'_preview.csv')).open('w', encoding='utf-8-sig', newline='') as f:
                        rows = ([{'test_id': str(u['_id']), 'name': u['display_name'], **u['demographics']} for u in docs[name]]
                                if name == 'users' else [{'number': o['order_number'], 'user_id': str(o['user_id']),
                                    'taipei_time': o['ordered_at'].astimezone(TZ).isoformat(), 'status': o['status'],
                                    'payment': o['payment_status'], 'amount': str(o['total_amount'].to_decimal()), 'is_demo': True} for o in docs[name]])
                        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
                print(json.dumps({'generated': {n:len(v) for n,v in docs.items()}, 'offline_invariants': 'passed'}))
            elif args.action == 'migrate':
                migrate(db); print('Additive schema migration verified')
            else:
                docs = load(OUT/'dataset.extjson'); catalog = load(OUT/'catalog_snapshot.extjson')
                manifest = load(OUT/'manifest.json')
                require(digest(docs) == manifest['dataset_sha256'], 'Artifact hash mismatch')
                validate(docs, catalog)
                if args.action == 'verify':
                    require(all(db[n].count_documents({'synthetic_batch_id':BATCH}) == len(v) for n,v in docs.items()), 'Incomplete batch')
                report = run_import(db, docs, catalog, args.action in ('apply', 'verify'), args.action == 'verify')
                save(OUT/(args.action+'_report.json'), report)
                print(json.dumps({'action': args.action, 'passed': True, 'inserted':report['inserted']}))
    finally:
        os.close(fd); lock.unlink()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print a connection URI or arbitrary server document contents.
        print('Stopped: '+type(exc).__name__, file=sys.stderr)
        if isinstance(exc, ValueError):
            print(str(exc), file=sys.stderr)
        sys.exit(1)
