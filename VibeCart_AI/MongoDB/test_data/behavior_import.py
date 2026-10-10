"""D4 live-reference preflight, transaction rollback rehearsal and gated import.

Default preflight is read-only. No source documents, credentials or IDs are printed.
Only behavior_events can be written. Application requires deployment isolation evidence.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from bson import json_util
from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema_active_v4 import SCHEMAS, INDEXES
from behavior_fixture import build, validate, expected, BATCH, SOURCE_BATCH
from workflow import canonical, digest, require

HOST = 'vibecart-ai-free.odqe25w.mongodb.net'
BATCH_QUERY = {'metadata.synthetic_batch_id': BATCH}
CONSUMERS = {'admin_monitor', 'storefront_recommendation', 'scoring_scheduler', 'production_attribution'}


def connect(env_file):
    config = dotenv_values(env_file)
    require(urlparse(config.get('MONGO_URI', '')).hostname == HOST
            and config.get('MONGO_DB') == 'vibecart_ai', 'Unexpected database target')
    return MongoClient(config['MONGO_URI'], tz_aware=True, serverSelectionTimeoutMS=10000)


def source_snapshot(db, session=None):
    def rows(name, query, fields):
        return list(db[name].find(query, {k: 1 for k in fields}, session=session))
    orders = rows('orders', {'synthetic_batch_id': SOURCE_BATCH},
                  ['_id', 'user_id', 'synthetic_batch_id', 'is_demo', 'payment_status', 'status', 'ordered_at'])
    require(orders, 'Source batch missing')
    items = rows('order_items', {'order_id': {'$in': [o['_id'] for o in orders]}},
                 ['_id', 'order_id', 'user_id', 'product_id', 'quantity'])
    users = rows('users', {'_id': {'$in': list({o['user_id'] for o in orders})}}, ['_id', 'registered_at'])
    products = rows('products', {'_id': {'$in': list({i['product_id'] for i in items})}},
                    ['_id', 'major_category_id', 'minor_category_id'])
    return {'orders': orders, 'order_items': items, 'users': users}, {'products': products}


def check_schema(db):
    opts = db.behavior_events.options()
    require(opts.get('validator') == SCHEMAS['behavior_events']
            and opts.get('validationLevel') == 'strict' and opts.get('validationAction') == 'error',
            'Behavior validator drift')
    actual = {i['name']: i for i in db.behavior_events.list_indexes()}
    require(set(actual) == {'_id_'} | {m.document['name'] for m in INDEXES['behavior_events']}, 'Index drift')
    for model in INDEXES['behavior_events']:
        wanted = model.document
        found = actual[wanted['name']]
        require(list(found['key'].items()) == list(wanted['key'].items())
                and bool(found.get('unique')) == bool(wanted.get('unique')), 'Index option drift')


def missing_rows(events, existing):
    wanted = {e['_id']: e for e in events}
    by_event = {e['event_id']: e for e in events}
    require(len(wanted) == len(events) == len(by_event), 'Duplicate planned event')
    found = set()
    for row in existing:
        require(row['_id'] in wanted and row.get('event_id') in by_event, 'Unplanned collision/batch row')
        require(canonical(row) == canonical(wanted[row['_id']]), 'Existing event differs; overwrite refused')
        require(row['_id'] not in found, 'Duplicate stored identity')
        found.add(row['_id'])
    return [e for e in events if e['_id'] not in found]


def existing_rows(db, events, session=None):
    return list(db.behavior_events.find({'$or': [BATCH_QUERY,
        {'_id': {'$in': [e['_id'] for e in events]}},
        {'event_id': {'$in': [e['event_id'] for e in events]}}]}, session=session))


def isolation_evidence(path):
    require(path is not None, 'Deployment isolation evidence required')
    evidence = json.loads(Path(path).read_text(encoding='utf-8'))
    require(evidence.get('database') == 'vibecart_ai' and evidence.get('batch') == BATCH
            and evidence.get('deployment_ref') and evidence.get('checked_at'), 'Isolation evidence scope missing')
    require(set(evidence.get('consumer_checks', {})) == CONSUMERS
            and all(v == 'passed' for v in evidence['consumer_checks'].values()), 'Consumer isolation incomplete')
    return digest(evidence)


def run(db, action='preflight', max_orders=100, evidence=None):
    require(db.name == 'vibecart_ai', 'Unexpected database')
    require(action in {'preflight', 'dry-run', 'apply', 'verify'}, 'Invalid action')
    evidence_hash = isolation_evidence(evidence) if action == 'apply' else None
    check_schema(db)
    data, catalog = source_snapshot(db)
    events = build(data, catalog, max_orders)
    validate(events, data, catalog)
    absent = missing_rows(events, existing_rows(db, events))
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'database': db.name,
              'action': action, 'batch': BATCH, 'status': 'passed',
              'expected': expected(events), 'dataset_sha256': digest(events),
              'existing': len(events) - len(absent), 'missing': len(absent),
              'committed': False, 'inserted': 0, 'rollback_rehearsal': False,
              'isolation_evidence_sha256': evidence_hash}
    if action == 'verify':
        require(not absent, 'Batch incomplete')
    if action in {'dry-run', 'apply'}:
        before = db.behavior_events.count_documents(BATCH_QUERY)
        with db.client.start_session() as session:
            session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority'))
            try:
                live_data, live_catalog = source_snapshot(db, session)
                require(digest(build(live_data, live_catalog, max_orders)) == digest(events), 'Source changed')
                absent = missing_rows(events, existing_rows(db, events, session))
                for offset in range(0, len(absent), 200):
                    db.behavior_events.insert_many(absent[offset:offset+200], session=session)
                readback = list(db.behavior_events.find(BATCH_QUERY, session=session))
                require(not missing_rows(events, readback), 'Transaction readback incomplete')
                if action == 'apply': session.commit_transaction()
                else: session.abort_transaction()
            except Exception:
                if session.in_transaction: session.abort_transaction()
                raise
        report.update(committed=action == 'apply', inserted=len(absent) if action == 'apply' else 0,
                      rollback_rehearsal=action == 'dry-run')
        after = db.behavior_events.count_documents(BATCH_QUERY)
        require(after == before + (len(absent) if action == 'apply' else 0), 'Batch count changed unexpectedly')
        require(digest(build(*source_snapshot(db), max_orders)) == digest(events), 'Source changed after operation')
        if action == 'apply':
            require(not missing_rows(events, existing_rows(db, events)), 'Committed readback incomplete')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'dry-run', 'apply', 'verify'])
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--max-orders', type=int, default=100)
    parser.add_argument('--isolation-evidence')
    args = parser.parse_args()
    # Reserve evidence destination before any possible committed write.
    with Path(args.report).open('x', encoding='utf-8') as output:
        try:
            with connect(args.env_file) as client:
                report = run(client.vibecart_ai, args.action, args.max_orders, args.isolation_evidence)
            output.write(json_util.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({k: report[k] for k in ('status', 'action', 'existing', 'missing', 'committed', 'inserted')}))
        except Exception as error:
            failure = {'status': 'error', 'action': args.action, 'error_type': type(error).__name__,
                       'message': 'No completion claimed; inspect target, schema, source and transaction evidence.'}
            output.write(json.dumps(failure, indent=2) + '\n')
            print(json.dumps(failure))
            return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
