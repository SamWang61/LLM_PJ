"""Read-only v4 readiness audit. No schema changes, inserts or sample-data output."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'VibeCart_AI/MongoDB'))
from schema_complete_v4 import SCHEMAS, INDEXES

MIGRATIONS = {'20260916_01_initial_schema_v2', '20260916_02_cart_state_events_v3',
              '20260918_03_schema_document_constraints', '20260918_04_complete_catalog_schema_v4'}
RELATIONSHIPS = [('products', 'major_category_id', 'categories'),
                 ('products', 'minor_category_id', 'categories'),
                 ('product_skus', 'product_id', 'products'),
                 ('carts', 'user_id', 'users'), ('orders', 'user_id', 'users'),
                 ('order_items', 'order_id', 'orders'), ('order_items', 'user_id', 'users'),
                 ('order_items', 'product_id', 'products'), ('order_items', 'sku_id', 'product_skus'),
                 ('product_reviews', 'user_id', 'users'), ('product_reviews', 'order_item_id', 'order_items'),
                 ('product_reviews', 'product_id', 'products')]


def index_differences(actual, expected):
    problems = []
    if set(actual) != {'_id_'} | {m.document['name'] for m in expected}:
        problems.append('index_names')
    for model in expected:
        wanted = model.document
        found = actual.get(wanted['name'])
        if not found:
            continue
        for field, value in wanted.items():
            if field == 'key':
                if 'text' in value.values():
                    matches = found.get('weights') == {'name': 1, 'description': 1}
                else:
                    # Compound index key order matters; plain dict equality does not.
                    matches = list(found.get('key', {}).items()) == list(value.items())
            else:
                matches = found.get(field) == value
            if not matches:
                problems.append('index:' + wanted['name'] + ':' + field)
        for field in ('unique', 'partialFilterExpression', 'expireAfterSeconds', 'sparse'):
            if found.get(field) != wanted.get(field):
                problems.append('index:' + wanted['name'] + ':' + field)
    return sorted(set(problems))


def audit(db, *, relationships=False):
    names = set(db.list_collection_names())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'mode': 'read_only',
              'status': 'passed', 'collections': [], 'issues': [], 'relationships': [],
              'extra_collections_count': len(names - set(SCHEMAS))}
    for name, validator in SCHEMAS.items():
        row = {'name': name, 'issues': []}
        if name not in names:
            row['issues'].append('missing_collection')
        else:
            collection = db[name]
            options = collection.options()
            for field, expected in [('validator', validator), ('validationLevel', 'strict'), ('validationAction', 'error')]:
                if options.get(field) != expected:
                    row['issues'].append(field)
            actual = {i['name']: i for i in collection.list_indexes()}
            row['issues'] += index_differences(actual, INDEXES[name])
            row['indexes'] = len(actual)
            row['documents'] = collection.count_documents({})
            row['conforming'] = collection.count_documents(validator)
            if row['documents'] != row['conforming']:
                row['issues'].append('nonconforming_documents_or_concurrent_change')
        report['collections'].append(row)
    migration_rows = list(db.schema_migrations.find({}, {'_id': 1, 'status': 1})) if 'schema_migrations' in names else []
    report['expected_migrations'] = [{'id': name, 'succeeded': any(r['_id'] == name and r.get('status') == 'succeeded'
                                      for r in migration_rows)} for name in sorted(MIGRATIONS)]
    if not all(r['succeeded'] for r in report['expected_migrations']):
        report['issues'].append('missing_or_unsuccessful_migration')
    if any(r.get('status') != 'succeeded' for r in migration_rows):
        report['issues'].append('unfinished_or_failed_migration')
    report['extra_migrations_count'] = sum(r['_id'] not in MIGRATIONS for r in migration_rows)
    if report['extra_migrations_count']:
        report['issues'].append('unexpected_migration_history')
    if report['extra_collections_count']:
        report['issues'].append('unexpected_collections_review_required')
    if 'system_configs' in names:
        policy_count = db.system_configs.count_documents({'config_key': 'recommendation_policy', 'status': 'active'})
        report['active_recommendation_policies'] = policy_count
        if policy_count != 1:
            report['issues'].append('expected_one_active_policy')
    if relationships:
        for source, field, target in RELATIONSHIPS:
            if source not in names or target not in names:
                continue
            result = list(db[source].aggregate([
                {'$match': {'schema_version': 4}},
                {'$lookup': {'from': target, 'localField': field, 'foreignField': '_id', 'as': '_audit_parent'}},
                {'$match': {'_audit_parent': {'$size': 0}}}, {'$count': 'orphans'}]))
            count = result[0]['orphans'] if result else 0
            report['relationships'].append({'source': source, 'field': field, 'target': target, 'orphans': count})
        if any(r['orphans'] for r in report['relationships']):
            report['issues'].append('orphan_references')
    report['total_indexes'] = sum(r.get('indexes', 0) for r in report['collections'])
    if report['issues'] or any(r['issues'] for r in report['collections']):
        report['status'] = 'failed'
    return report


def main():
    from dotenv import dotenv_values
    from pymongo import MongoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--report', required=True, help='New evidence file; existing files are never overwritten')
    parser.add_argument('--relationships', action='store_true')
    args = parser.parse_args()
    destination = Path(args.report)
    if destination.exists():
        raise ValueError('Choose a new evidence file')
    config = dotenv_values(args.env_file)
    if (urlparse(config.get('MONGO_URI', '')).hostname != 'vibecart-ai-free.odqe25w.mongodb.net'
            or config.get('MONGO_DB') != 'vibecart_ai' or config.get('DATA_MODE') != 'v4'):
        raise ValueError('Unexpected database target')
    with MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=10000, tz_aware=True) as client:
        report = audit(client[config['MONGO_DB']], relationships=args.relationships)
    # Only metadata/counts, never URI, user IDs, emails or document contents.
    with destination.open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'status': report['status'], 'collections': len(report['collections']),
                      'indexes': report['total_indexes'], 'relationships_checked': len(report['relationships'])}))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'error', 'error_type': type(error).__name__,
                          'message': 'Audit could not finish; no completion claimed. Check target, permissions and report path.'}))
        raise SystemExit(2)
