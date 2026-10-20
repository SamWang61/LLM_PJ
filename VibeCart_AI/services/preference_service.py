"""Bounded, opt-in v4 preference snapshots; never used by storefront requests.

Snapshot v1 keeps raw category caps and per-event product decay. It is not the
request-time 6+4 ranker. Writes are atomic per score document, not across all
source collections; run in a maintenance window and rebuild after source edits.
"""
from copy import deepcopy
from datetime import datetime, timezone
import math

from bson import BSON, ObjectId
from pymongo.errors import DuplicateKeyError

ACTIONS = ('PURCHASE', 'ADD_TO_CART', 'SEARCH', 'PRODUCT_VIEW')
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


class ScoreError(ValueError):
    pass


class ScoreConflict(ScoreError):
    pass


def utc(value):
    if not isinstance(value, datetime):
        raise ScoreError('Invalid event time')
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def validate_policy(policy):
    if (not isinstance(policy, dict) or policy.get('status') != 'active'
            or type(policy.get('version')) is not int or policy['version'] != 1):
        raise ScoreError('Only active score policy version 1 is supported')
    settings = policy.get('settings')
    if not isinstance(settings, dict):
        raise ScoreError('Invalid scoring policy')
    for action in ACTIONS:
        for field, minimum in (('weights', 0), ('half_life_days', 1)):
            values = settings.get(field)
            value = values.get(action) if isinstance(values, dict) else None
            try:
                valid = type(value) is int and value >= minimum and math.isfinite(float(value))
            except OverflowError:
                valid = False
            if not valid:
                raise ScoreError('Invalid scoring policy')
    if (type(settings.get('major_score_cap')) is not int or settings['major_score_cap'] != 70
            or type(settings.get('minor_score_cap')) is not int or settings['minor_score_cap'] != 30):
        raise ScoreError('Unexpected category caps')
    return settings


def synthetic(event):
    metadata = event.get('metadata', {})
    if not isinstance(metadata, dict):
        raise ScoreError('Invalid event metadata')
    return metadata.get('synthetic') is True or metadata.get('synthetic_batch_id') not in (None, '')


def unique_events(user_id, events, as_of):
    """Validate and deduplicate before purchase eligibility can hide conflicts."""
    if not isinstance(user_id, ObjectId):
        raise ScoreError('Invalid member')
    as_of = utc(as_of)
    seen, rows = {}, []
    for event in events:
        if not isinstance(event, dict):
            raise ScoreError('Invalid event')
        if synthetic(event):
            continue
        if event.get('user_id') != user_id:
            raise ScoreError('Mixed member events')
        when = utc(event.get('event_at'))
        if when > as_of:
            continue
        if (type(event.get('score_version')) is not int or event['score_version'] != 1
                or event.get('event_type') not in ACTIONS):
            raise ScoreError('Unsupported event version or type')
        identity = event.get('event_id')
        if not isinstance(identity, str) or not identity or len(identity) > 128:
            raise ScoreError('Invalid event identity')
        for key in ('product_id', 'major_category_id', 'minor_category_id', 'order_id'):
            if event.get(key) is not None and not isinstance(event[key], ObjectId):
                raise ScoreError('Expected v4 ObjectId reference')
        quantity = event.get('quantity', 1)
        if type(quantity) is not int or quantity < 1:
            raise ScoreError('Invalid event quantity')
        query_text = event.get('search_query')
        if query_text is not None and (not isinstance(query_text, str) or len(query_text) > 200):
            raise ScoreError('Invalid search text')
        signature = tuple(event.get(k) for k in ('user_id', 'event_type', 'product_id',
            'major_category_id', 'minor_category_id', 'order_id', 'search_query')) + (quantity, when)
        if identity in seen:
            if seen[identity] != signature:
                raise ScoreError('Conflicting duplicate event identity')
            continue
        seen[identity] = signature
        rows.append((event, when))
    return sorted(rows, key=lambda row: (row[1], row[0]['event_id']))


def calculate_scores(user_id, events, policy, as_of):
    """Snapshot v1: capped raw categories, per-event decayed product scores."""
    settings, as_of = validate_policy(policy), utc(as_of)
    result = dict(schema_version=4, user_id=user_id, score_version=1,
                  major_categories={}, minor_categories={}, products={},
                  cross_category_scores={}, last_processed_event_at=None, updated_at=as_of)
    for event, when in unique_events(user_id, events, as_of):
        action = event['event_type']
        weight = float(settings['weights'][action])
        decay = 0.5 ** ((as_of - when).total_seconds() / 86400 / settings['half_life_days'][action])
        for bucket, reference, cap in (('major_categories', 'major_category_id', 70),
                                       ('minor_categories', 'minor_category_id', 30),
                                       ('products', 'product_id', None)):
            reference_id = event.get(reference)
            if reference_id is None:
                continue
            row = result[bucket].setdefault(str(reference_id), dict(raw_score=0.0, score=0.0, last_event_at=when))
            row['raw_score'] += weight
            row['score'] = min(row['raw_score'], float(cap)) if cap else row['score'] + weight * decay
            if not math.isfinite(row['raw_score']) or not math.isfinite(row['score']):
                raise ScoreError('Nonfinite score')
            row['last_event_at'] = max(row['last_event_at'], when)
        result['last_processed_event_at'] = max(result['last_processed_event_at'] or when, when)
    return result


def active_member(db, user_id):
    return db.users.find_one({'_id': user_id, 'schema_version': 4, 'status': 'active', 'is_active': True})


def require_unique_member_index(collection):
    for index in collection.list_indexes():
        if (index.get('unique') and list(index['key'].items()) == [('user_id', 1)]
                and not index.get('partialFilterExpression') and not index.get('sparse')):
            return
    raise ScoreError('A complete unique user_id score index is required')


def rebuild_member(db, user_id, *, as_of=None, apply=False, max_events=10000):
    """Replace one bounded snapshot, with an exact preimage compare-and-swap.

    Source changes after the final checks converge on the next rebuild. This is
    an operator batch, not a member session or a cross-collection transaction.
    """
    if (not isinstance(user_id, ObjectId) or type(max_events) is not int
            or not 1 <= max_events <= 100000 or type(apply) is not bool):
        raise ScoreError('Invalid member or event limit')
    as_of = utc(as_of if as_of is not None else datetime.now(timezone.utc))
    as_of = as_of.replace(microsecond=(as_of.microsecond // 1000) * 1000)
    if not active_member(db, user_id):
        raise ScoreError('Active v4 member required')
    policies = list(db.system_configs.find({'config_key': 'recommendation_policy', 'status': 'active'}).limit(2))
    if len(policies) != 1:
        raise ScoreError('Exactly one active recommendation policy is required')
    policy = policies[0]
    validate_policy(policy)
    scores = db.user_preference_scores
    if apply:
        require_unique_member_index(scores)
        if not scores.write_concern.acknowledged:
            raise ScoreError('Acknowledged writes required')
    previous = scores.find_one({'user_id': user_id})
    if previous and utc(previous.get('updated_at')) > as_of:
        raise ScoreConflict('Cannot replace a newer score snapshot')
    # Exclude synthetic before sorting/limiting; fixture volume cannot crowd out
    # a member's normal history or trigger a false overflow.
    query = {'user_id': user_id, 'event_at': {'$lte': as_of},
             'metadata.synthetic': {'$ne': True}, 'metadata.synthetic_batch_id': {'$in': [None, '']}}
    events = list(db.behavior_events.find(query).sort([('event_at', 1), ('event_id', 1)]).limit(max_events + 1))
    if len(events) > max_events:
        raise ScoreError('Event limit exceeded; no partial scores written')
    unique = [event for event, _ in unique_events(user_id, events, as_of)]
    purchase_ids = list({e['order_id'] for e in unique if e.get('event_type') == 'PURCHASE' and e.get('order_id')})
    # Personalization includes a real member's demo purchases; attribution stays
    # independent and continues to exclude demo conversions.
    valid_orders = {o['_id'] for o in db.orders.find({'_id': {'$in': purchase_ids}, 'user_id': user_id,
        'schema_version': 4, 'payment_status': 'paid', 'status': {'$ne': 'cancelled'}}, {'_id': 1})}
    eligible = [e for e in unique if e.get('event_type') != 'PURCHASE' or e.get('order_id') in valid_orders]
    snapshot = calculate_scores(user_id, eligible, policy, as_of)
    snapshot['cross_category_scores'] = deepcopy((previous or {}).get('cross_category_scores', {}))
    snapshot['_id'] = previous['_id'] if previous else ObjectId()
    if len(BSON.encode(snapshot)) > MAX_SNAPSHOT_BYTES:
        raise ScoreError('Snapshot too large; no scores written')
    if apply:
        if not active_member(db, user_id):
            raise ScoreConflict('Member changed; rebuild after maintenance')
        current_policies = list(db.system_configs.find({'config_key': 'recommendation_policy', 'status': 'active'}).limit(2))
        if current_policies != [policy]:
            raise ScoreConflict('Policy changed; rebuild with the current policy')
        if previous:
            # The literal full preimage also catches concurrent new fields and
            # cross-category edits, including updates in the same millisecond.
            fence = {'_id': previous['_id'], '$expr': {'$eq': ['$$ROOT', {'$literal': previous}]}}
            if scores.replace_one(fence, snapshot).matched_count != 1:
                raise ScoreConflict('Concurrent score update; retry')
        else:
            try:
                scores.insert_one(snapshot)
            except DuplicateKeyError:
                raise ScoreConflict('Concurrent score creation; retry') from None
    return {'applied': apply, 'events_read': len(events), 'events_scored': len(eligible),
            'excluded_purchase_events': len(unique) - len(eligible), 'snapshot': snapshot}
