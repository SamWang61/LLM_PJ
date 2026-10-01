from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import mongomock
import pytest
from bson import ObjectId, BSON

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from VibeCart_AI.services.preference_service import calculate_scores, rebuild_member, ScoreError, ScoreConflict

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)
USER, PRODUCT, MAJOR, MINOR = [ObjectId() for _ in range(4)]


def policy():
    return {'config_key': 'recommendation_policy', 'status': 'active', 'version': 1,
            'settings': {'weights': {'PURCHASE': 4, 'ADD_TO_CART': 3, 'SEARCH': 2, 'PRODUCT_VIEW': 1},
                         'half_life_days': {'PURCHASE': 365, 'ADD_TO_CART': 180, 'SEARCH': 90, 'PRODUCT_VIEW': 30},
                         'major_score_cap': 70, 'minor_score_cap': 30}}


def event(key='view', **updates):
    return {'event_id': key, 'score_version': 1, 'event_type': 'PRODUCT_VIEW',
            'user_id': USER, 'product_id': PRODUCT, 'major_category_id': MAJOR,
            'minor_category_id': MINOR, 'event_at': NOW, 'quantity': 1, **updates}


@pytest.mark.parametrize('action,days,weight', [('PRODUCT_VIEW', 30, 1), ('SEARCH', 90, 2),
                                               ('ADD_TO_CART', 180, 3), ('PURCHASE', 365, 4)])
def test_exact_half_life(action, days, weight):
    score = calculate_scores(USER, [event(event_type=action, event_at=NOW-timedelta(days=days))], policy(), NOW)
    assert score['products'][str(PRODUCT)]['score'] == weight / 2
    assert score['major_categories'][str(MAJOR)]['score'] == weight


def test_caps_unique_events_quantity_and_future():
    events = [event(str(i), event_type='PURCHASE', quantity=99) for i in range(30)]
    events += [events[0], event('future', event_at=NOW+timedelta(days=1))]
    score = calculate_scores(USER, events, policy(), NOW)
    assert score['major_categories'][str(MAJOR)]['score'] == 70
    assert score['minor_categories'][str(MINOR)]['score'] == 30
    assert score['products'][str(PRODUCT)]['raw_score'] == 120
    assert score['products'][str(PRODUCT)]['score'] == 120
    assert BSON.encode(score)


def test_conflicting_duplicate_rejected():
    with pytest.raises(ScoreError):
        calculate_scores(USER, [event(), event(event_type='PURCHASE')], policy(), NOW)


def test_unmapped_search_no_guessed_interests():
    score = calculate_scores(USER, [event(event_type='SEARCH', product_id=None,
                             major_category_id=None, minor_category_id=None)], policy(), NOW)
    assert score['products'] == score['major_categories'] == score['minor_categories'] == {}
    assert score['last_processed_event_at'] == NOW


@pytest.fixture
def db():
    db = mongomock.MongoClient(tz_aware=True).test
    db.users.insert_one({'_id': USER, 'schema_version': 4, 'status': 'active', 'is_active': True})
    db.system_configs.insert_one(policy())
    db.user_preference_scores.create_index('user_id', unique=True)
    return db


def test_dry_run_apply_rerun_decay_and_cross_preserved(db):
    db.behavior_events.insert_one(event())
    preview = rebuild_member(db, USER, as_of=NOW)
    assert not preview['applied'] and db.user_preference_scores.count_documents({}) == 0
    first = rebuild_member(db, USER, as_of=NOW, apply=True)['snapshot']
    second = rebuild_member(db, USER, as_of=NOW, apply=True)['snapshot']
    assert first == second
    cross = {'x': {'raw_score': 2.0, 'score': 2.0, 'last_event_at': NOW}}
    db.user_preference_scores.update_one({'user_id': USER}, {'$set': {'cross_category_scores': cross}})
    later = rebuild_member(db, USER, as_of=NOW+timedelta(days=30), apply=True)['snapshot']
    assert later['products'][str(PRODUCT)]['score'] == .5
    assert later['cross_category_scores'] == cross
    with pytest.raises(ScoreConflict):
        rebuild_member(db, USER, as_of=NOW, apply=True)


def test_unpaid_demo_refund_cancelled_missing_and_other_member_purchases(db):
    for i, updates in enumerate([{}, {'is_demo': True}, {'payment_status': 'refunded'},
                                 {'status': 'cancelled'}, {'payment_status': 'unpaid'}, {'user_id': ObjectId()}]):
        oid = db.orders.insert_one({'user_id': USER, 'schema_version': 4, 'payment_status': 'paid',
                                    'status': 'confirmed', 'is_demo': False, **updates}).inserted_id
        db.behavior_events.insert_one(event(str(i), event_type='PURCHASE', order_id=oid))
    db.behavior_events.insert_one(event('missing', event_type='PURCHASE', order_id=ObjectId()))
    result = rebuild_member(db, USER, as_of=NOW)
    assert result['events_scored'] == 1 and result['excluded_purchase_events'] == 6
    assert result['snapshot']['products'][str(PRODUCT)]['score'] == 4


def test_overflow_never_replaces_snapshot(db):
    db.behavior_events.insert_one(event())
    previous = rebuild_member(db, USER, as_of=NOW, apply=True)['snapshot']
    db.behavior_events.insert_one(event('two'))
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True, max_events=1)
    assert db.user_preference_scores.find_one({'user_id': USER}) == previous


def test_unsupported_event_and_policy_fail_closed(db):
    db.behavior_events.insert_one(event(score_version=2))
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0
    db.system_configs.update_one({}, {'$set': {'version': 2}})
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW)


def test_concurrent_update_not_overwritten(db, monkeypatch):
    rebuild_member(db, USER, as_of=NOW, apply=True)
    original = db.user_preference_scores.replace_one
    def competing(query, replacement):
        db.user_preference_scores.update_one({'user_id': USER}, {'$set': {'updated_at': NOW+timedelta(seconds=1)}})
        return original(query, replacement)
    monkeypatch.setattr(db.user_preference_scores, 'replace_one', competing)
    with pytest.raises(ScoreConflict):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.find_one({'user_id': USER})['updated_at'] > NOW
