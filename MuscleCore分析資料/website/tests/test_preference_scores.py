"""Snapshot-v1 contracts; real MongoDB CAS lives in the persistence suite."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import mongomock
import pytest
from bson import ObjectId, BSON
from pymongo.results import UpdateResult

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from VibeCart_AI.services import preference_service as scoring
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
            'minor_category_id': MINOR, 'event_at': NOW, 'quantity': 1, 'metadata': {}, **updates}


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


def test_dry_run_first_apply_then_readonly_decay_and_cross_preserved(db):
    db.behavior_events.insert_one(event())
    preview = rebuild_member(db, USER, as_of=NOW)
    assert not preview['applied'] and db.user_preference_scores.count_documents({}) == 0
    first = rebuild_member(db, USER, as_of=NOW, apply=True)['snapshot']
    cross = {'x': {'raw_score': 2.0, 'score': 2.0, 'last_event_at': NOW}}
    db.user_preference_scores.update_one({'user_id': USER}, {'$set': {'cross_category_scores': cross}})
    later = rebuild_member(db, USER, as_of=NOW+timedelta(days=30))['snapshot']
    assert later['products'][str(PRODUCT)]['score'] == .5
    assert later['cross_category_scores'] == cross
    assert db.user_preference_scores.find_one({'user_id': USER})['updated_at'] == first['updated_at']
    with pytest.raises(ScoreConflict):
        rebuild_member(db, USER, as_of=NOW-timedelta(seconds=1), apply=True)


def test_paid_demo_personalizes_but_invalid_purchases_do_not_and_events_are_unchanged(db):
    for i, updates in enumerate([{}, {'is_demo': True}, {'payment_status': 'refunded'},
                                 {'status': 'cancelled'}, {'payment_status': 'unpaid'}, {'user_id': ObjectId()},
                                 {'schema_version': 3}]):
        oid = db.orders.insert_one({'user_id': USER, 'schema_version': 4, 'payment_status': 'paid',
                                    'status': 'confirmed', 'is_demo': False, **updates}).inserted_id
        metadata = {'demo_checkout': True, 'exclude_from_attribution': True} if updates.get('is_demo') else {}
        db.behavior_events.insert_one(event(str(i), event_type='PURCHASE', order_id=oid, metadata=metadata))
    db.behavior_events.insert_one(event('missing', event_type='PURCHASE', order_id=ObjectId()))
    before = list(db.behavior_events.find())
    result = rebuild_member(db, USER, as_of=NOW, apply=True)
    assert result['events_scored'] == 2 and result['excluded_purchase_events'] == 6
    assert result['snapshot']['products'][str(PRODUCT)]['score'] == 8
    assert list(db.behavior_events.find()) == before


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
    def competing(query, replacement, **kwargs):
        db.user_preference_scores.update_one({'user_id': USER}, {'$set': {'updated_at': NOW+timedelta(seconds=1)}})
        return UpdateResult({'n': 0, 'nModified': 0}, acknowledged=True)
    monkeypatch.setattr(db.user_preference_scores, 'replace_one', competing)
    with pytest.raises(ScoreConflict):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.find_one({'user_id': USER})['updated_at'] > NOW


def test_each_event_has_its_own_decay_age_and_categories_keep_raw_totals():
    result = calculate_scores(USER, [event('old', event_at=NOW-timedelta(days=30)), event('new')], policy(), NOW)
    assert result['products'][str(PRODUCT)]['score'] == 1.5
    assert result['products'][str(PRODUCT)]['raw_score'] == 2
    assert result['major_categories'][str(MAJOR)]['score'] == 2


@pytest.mark.parametrize('updates', [
    {'product_id': ObjectId()}, {'major_category_id': ObjectId()}, {'minor_category_id': ObjectId()},
    {'quantity': 2}, {'order_id': ObjectId()}, {'event_at': NOW-timedelta(seconds=1)},
    {'search_query': 'different query'},
])
def test_same_event_id_rejects_changes_to_all_scoring_inputs(updates):
    with pytest.raises(ScoreError):
        calculate_scores(USER, [event(), event(**updates)], policy(), NOW)


@pytest.mark.parametrize('metadata', [
    {'synthetic': True}, {'synthetic_batch_id': 'other-batch'},
    {'synthetic': False, 'synthetic_batch_id': 'marked-by-batch'},
])
def test_pure_calculation_excludes_each_synthetic_marker(metadata):
    clean = event('normal')
    marked = event('synthetic', event_type='ADD_TO_CART', metadata=metadata)
    assert calculate_scores(USER, [clean, marked], policy(), NOW) == calculate_scores(USER, [clean], policy(), NOW)


@pytest.mark.parametrize('metadata', [None, [], '', False])
def test_explicit_non_object_event_metadata_is_rejected(metadata):
    with pytest.raises(ScoreError):
        calculate_scores(USER, [event(metadata=metadata)], policy(), NOW)


@pytest.mark.parametrize('metadata', [{'synthetic': True}, {'synthetic_batch_id': 'batch-only'}])
def test_query_excludes_synthetic_before_sort_and_limit(db, metadata):
    db.behavior_events.insert_many([
        event('synthetic-' + str(i), event_at=NOW-timedelta(days=1), metadata=metadata)
        for i in range(10)
    ] + [event('normal-a'), event('normal-b')])
    result = rebuild_member(db, USER, as_of=NOW, max_events=2)
    assert result['events_read'] == result['events_scored'] == 2
    assert result['snapshot']['products'][str(PRODUCT)]['raw_score'] == 2
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('updates', [{'status': 'inactive'}, {'is_active': False}, {'schema_version': 3}])
def test_only_active_v4_members_may_rebuild(db, updates):
    db.users.update_one({'_id': USER}, {'$set': updates})
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('user,maximum', [('not-an-object-id', 1), (USER, True), (USER, 0), (USER, 100001)])
def test_member_and_event_bounds_fail_without_writing(db, user, maximum):
    with pytest.raises(ScoreError):
        rebuild_member(db, user, as_of=NOW, apply=True, max_events=maximum)
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('change', ['bool-version', 'inactive', 'missing-settings', 'half-life',
                                    'bool-weight', 'float-major-cap', 'float-minor-cap'])
def test_invalid_policy_fails_closed_with_score_error(db, change):
    bad = policy()
    if change == 'bool-version': bad['version'] = True
    elif change == 'inactive': bad['status'] = 'inactive'
    elif change == 'missing-settings': del bad['settings']
    elif change == 'half-life': bad['settings']['half_life_days']['PURCHASE'] = 0
    elif change == 'bool-weight': bad['settings']['weights']['PURCHASE'] = True
    elif change == 'float-major-cap': bad['settings']['major_score_cap'] = 70.0
    elif change == 'float-minor-cap': bad['settings']['minor_score_cap'] = 30.0
    db.system_configs.replace_one({}, bad)
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('index', [None, {'user_id': 1}, {'user_id': 1, 'score_version': 1}])
def test_apply_service_requires_member_unique_index(db, index):
    db.user_preference_scores.drop_indexes()
    if index is not None:
        db.user_preference_scores.create_index(list(index.items()), unique=len(index) > 1)
    db.behavior_events.insert_one(event())
    assert not rebuild_member(db, USER, as_of=NOW)['applied']
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('index_options', [{'partialFilterExpression': {'schema_version': 4}}, {'sparse': True}])
def test_apply_rejects_partial_or_sparse_unique_member_index(db, index_options):
    db.user_preference_scores.drop_indexes()
    db.user_preference_scores.create_index('user_id', unique=True, **index_options)
    assert not rebuild_member(db, USER, as_of=NOW)['applied']
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


def test_conflicting_purchase_identity_is_rejected_before_purchase_eligibility_filter(db):
    db.behavior_events.insert_many([event('same-id'),
        event('same-id', event_type='PURCHASE', order_id=ObjectId())])
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


def test_unsupported_purchase_is_rejected_even_if_its_order_is_missing(db):
    db.behavior_events.insert_one(event(event_type='PURCHASE', score_version=2, order_id=ObjectId()))
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


@pytest.mark.parametrize('change', ['member', 'policy', 'second-policy'])
def test_apply_rechecks_member_and_policy_after_calculation(db, monkeypatch, change):
    db.behavior_events.insert_one(event())
    calculate = scoring.calculate_scores
    def changed_during_calculation(*args, **kwargs):
        result = calculate(*args, **kwargs)
        if change == 'member':
            db.users.update_one({'_id': USER}, {'$set': {'status': 'inactive', 'is_active': False}})
        elif change == 'second-policy':
            db.system_configs.insert_one(policy())
        else:
            db.system_configs.update_one({}, {'$set': {'settings.weights.PRODUCT_VIEW': 2}})
        return result
    monkeypatch.setattr(scoring, 'calculate_scores', changed_during_calculation)
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


def test_snapshot_size_limit_preserves_existing_document(db):
    db.behavior_events.insert_one(event())
    previous = rebuild_member(db, USER, as_of=NOW, apply=True)['snapshot']
    cross = {'x' * (8 * 1024 * 1024): {'raw_score': 1.0, 'score': 1.0, 'last_event_at': NOW}}
    db.user_preference_scores.update_one({'user_id': USER}, {'$set': {'cross_category_scores': cross}})
    with pytest.raises(ScoreError):
        rebuild_member(db, USER, as_of=NOW+timedelta(seconds=1), apply=True)
    current = db.user_preference_scores.find_one({'user_id': USER})
    assert current['updated_at'] == previous['updated_at'] and current['cross_category_scores'] == cross
