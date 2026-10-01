"""Bounded, private v4 score job. Default: read-only; never prints credentials."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bson import ObjectId
from dotenv import dotenv_values
from pymongo import MongoClient
from VibeCart_AI.services.preference_service import rebuild_member, ScoreError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--user-id', action='append', required=True, help='Explicit member ObjectId; repeat for a batch')
    parser.add_argument('--max-events', type=int, default=10000)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database-confirm', help='Must match configured database when applying')
    args = parser.parse_args()
    config = dotenv_values(args.env_file)
    if config.get('DATA_MODE') != 'v4' or not config.get('MONGO_URI') or not config.get('MONGO_DB'):
        raise ScoreError('Explicit v4 connection required')
    if args.apply and args.database_confirm != config['MONGO_DB']:
        raise ScoreError('Confirm database name before applying')
    if len(args.user_id) > 100:
        raise ScoreError('At most 100 explicit members per invocation')
    identities = list(dict.fromkeys(ObjectId(x) for x in args.user_id))
    totals = dict(mode='apply' if args.apply else 'dry_run', members=0, events_read=0,
                  events_scored=0, excluded_purchase_events=0)
    as_of = datetime.now(timezone.utc)
    with MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=10000, tz_aware=True) as client:
        db = client[config['MONGO_DB']]
        if args.apply and not any(i.get('unique') and list(i['key'].items()) == [('user_id', 1)]
                                 for i in db.user_preference_scores.list_indexes()):
            raise ScoreError('Unique member score index is required')
        for identity in identities:
            result = rebuild_member(db, identity, as_of=as_of, apply=args.apply, max_events=args.max_events)
            totals['members'] += 1
            for key in ('events_read', 'events_scored', 'excluded_purchase_events'):
                totals[key] += result[key]
            # One member is the commit unit; progress is visible if a later member fails.
            print(json.dumps(totals))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__,
                          'message': 'No credentials printed. Earlier member commits, if any, remain; rerun safely.'}))
        raise SystemExit(1)
