"""Rebuild v4 member scores from immutable events; no model or scheduler calls."""
from copy import deepcopy
from datetime import datetime, timezone
from bson import ObjectId, BSON
from pymongo.errors import DuplicateKeyError

ACTIONS = ('PURCHASE', 'ADD_TO_CART', 'SEARCH', 'PRODUCT_VIEW')


class ScoreError(ValueError):
    pass


class ScoreConflict(ScoreError):
    pass


def utc(value):
    if not isinstance(value, datetime):
        raise ScoreError('Invalid event time')
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def validate_policy(policy):
    if policy.get('status') != 'active' or policy.get('version') != 1:
        raise ScoreError('Only active score policy version 1 is supported')
    settings = policy['settings']
    for action in ACTIONS:
        for field, minimum in (('weights', 0), ('half_life_days', 1)):
            value = settings[field][action]
            if type(value) is not int or value < minimum:
                raise ScoreError('Invalid scoring policy')
    if settings['major_score_cap'] != 70 or settings['minor_score_cap'] != 30:
        raise ScoreError('Unexpected category caps')
    return settings


def calculate_scores(user_id, events, policy, as_of):
    """Categories use capped raw totals; product scores decay per event type.

    Each event contributes once, regardless of quantity. SEARCH contributes only
    to explicit category/product references; free text is never guessed.
    """
    settings = validate_policy(policy)
    as_of = utc(as_of)
    result = dict(schema_version=4, user_id=user_id, score_version=1,
                  major_categories={}, minor_categories={}, products={},
                  cross_category_scores={}, last_processed_event_at=None, updated_at=as_of)
    seen = {}
    for event in sorted(events, key=lambda e: (utc(e['event_at']), e['event_id'])):
        if event.get('user_id') != user_id:
            raise ScoreError('Mixed member events')
        when = utc(event['event_at'])
        if when > as_of:
            continue
        if event.get('score_version') != 1 or event.get('event_type') not in ACTIONS:
            raise ScoreError('Unsupported event version or type')
        event_id = event.get('event_id')
        if not isinstance(event_id, str) or not event_id:
            raise ScoreError('Missing event identity')
        signature = tuple(event.get(k) for k in ('user_id', 'event_type', 'product_id',
                          'major_category_id', 'minor_category_id', 'quantity', 'order_id')) + (when,)
        if event_id in seen:
            if seen[event_id] != signature:
                raise ScoreError('Conflicting duplicate event identity')
            continue
        seen[event_id] = signature
        action = event['event_type']
        weight = float(settings['weights'][action])
        decay = 0.5 ** ((as_of - when).total_seconds() / 86400 / settings['half_life_days'][action])
        for bucket, reference, cap in (('major_categories', 'major_category_id', 70),
                                       ('minor_categories', 'minor_category_id', 30),
                                       ('products', 'product_id', None)):
            identity = event.get(reference)
            if identity is None:
                continue
            if not isinstance(identity, ObjectId):
                raise ScoreError('Expected v4 ObjectId reference')
            row = result[bucket].setdefault(str(identity), dict(raw_score=0.0, score=0.0, last_event_at=when))
            row['raw_score'] += weight
            row['score'] = min(row['raw_score'], float(cap)) if cap else row['score'] + weight * decay
            row['last_event_at'] = max(row['last_event_at'], when)
        result['last_processed_event_at'] = when
    return result


def rebuild_member(db, user_id, *, as_of=None, apply=False, max_events=10000):
    """Dry-run by default. Replace one complete snapshot with optimistic locking.

    A later retry recomputes from events, so it does not double-add points. Do not
    mark events processed: this worker does not own other consumers' progress.
    """
    if not isinstance(user_id, ObjectId) or type(max_events) is not int or not 1 <= max_events <= 100000:
        raise ScoreError('Invalid member or event limit')
    as_of = utc(as_of or datetime.now(timezone.utc))
    # BSON dates have millisecond precision; use the same precision in comparisons.
    as_of = as_of.replace(microsecond=(as_of.microsecond // 1000) * 1000)
    if not db.users.find_one({'_id': user_id, 'schema_version': 4, 'status': 'active', 'is_active': True}):
        raise ScoreError('Active v4 member required')
    policy = db.system_configs.find_one({'config_key': 'recommendation_policy', 'status': 'active'})
    if not policy:
        raise ScoreError('No active recommendation policy')
    validate_policy(policy)
    previous = db.user_preference_scores.find_one({'user_id': user_id})
    if previous and utc(previous['updated_at']) > as_of:
        raise ScoreConflict('Cannot replace a newer score snapshot')
    events = list(db.behavior_events.find({'user_id': user_id, 'event_at': {'$lte': as_of}})
                  .sort([('event_at', 1), ('event_id', 1)]).limit(max_events + 1))
    if len(events) > max_events:
        raise ScoreError('Event limit exceeded; no partial scores written')
    purchase_ids = list({e['order_id'] for e in events if e.get('event_type') == 'PURCHASE' and e.get('order_id')})
    valid_orders = {o['_id'] for o in db.orders.find({'_id': {'$in': purchase_ids}, 'user_id': user_id,
                    'schema_version': 4, 'payment_status': 'paid', 'status': {'$ne': 'cancelled'}, 'is_demo': False}, {'_id': 1})}
    eligible = [e for e in events if e.get('event_type') != 'PURCHASE' or e.get('order_id') in valid_orders]
    snapshot = calculate_scores(user_id, eligible, policy, as_of)
    # A separate future association worker owns these values.
    snapshot['cross_category_scores'] = deepcopy((previous or {}).get('cross_category_scores', {}))
    snapshot['_id'] = previous['_id'] if previous else ObjectId()
    if len(BSON.encode(snapshot)) > 8 * 1024 * 1024:
        raise ScoreError('Snapshot too large; no scores written')
    if apply:
        current_policy = db.system_configs.find_one({'_id': policy['_id']})
        if current_policy != policy:
            raise ScoreConflict('Policy changed; retry with the current policy')
        if previous:
            # Compare the entire snapshot to avoid lost updates from another worker.
            replaced = db.user_preference_scores.replace_one(previous, snapshot)
            if replaced.matched_count != 1:
                raise ScoreConflict('Concurrent score update; retry')
        else:
            try:
                db.user_preference_scores.insert_one(snapshot)
            except DuplicateKeyError:
                raise ScoreConflict('Concurrent score creation; retry') from None
    return {'applied': apply, 'events_read': len(events), 'events_scored': len(eligible),
            'excluded_purchase_events': len(events) - len(eligible), 'snapshot': snapshot}
