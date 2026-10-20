"""Real, disposable localhost snapshots: strict schema, unique index and CAS.

These tests prove atomic score-document writes. They do not claim a transaction
across users, policies, orders and events or simulate an Atlas outage.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from threading import Barrier

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, OperationFailure

ROOT = Path(__file__).resolve().parents[3]
for location in (ROOT, ROOT / 'VibeCart_AI' / 'MongoDB', Path(__file__).resolve().parents[1]):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from schema_active_v4 import SCHEMAS
from schema_complete_v4 import default_policy
from test_ren_transactions import replica
from VibeCart_AI.services.preference_service import rebuild_member, ScoreError, ScoreConflict

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


def utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


@pytest.fixture
def score_db(replica):
    db, uid, pid, _ = replica
    db.create_collection('user_preference_scores', validator=SCHEMAS['user_preference_scores'],
                         validationLevel='strict', validationAction='error')
    db.user_preference_scores.create_index('user_id', unique=True)
    db.system_configs.insert_one(default_policy())
    category = db.products.find_one({'_id': pid})['major_category_id']
    db.behavior_events.insert_one({'_id': ObjectId(), 'schema_version': 4, 'event_id': 'local-score-view',
        'user_id': uid, 'event_type': 'PRODUCT_VIEW', 'product_id': pid,
        'major_category_id': category, 'minor_category_id': category, 'quantity': 1,
        'event_at': NOW, 'score_version': 1, 'metadata': {}})
    return db, uid, pid


def test_real_snapshot_matches_strict_validator_unique_index_and_idempotent_rerun(score_db):
    db, uid, pid = score_db
    assert db.user_preference_scores.count_documents({}) == 0
    assert not rebuild_member(db, uid, as_of=NOW)['applied']
    assert db.user_preference_scores.count_documents({}) == 0
    first = rebuild_member(db, uid, as_of=NOW, apply=True)['snapshot']
    second = rebuild_member(db, uid, as_of=NOW, apply=True)['snapshot']
    assert first == second
    assert db.user_preference_scores.count_documents(SCHEMAS['user_preference_scores']) == 1
    assert second['products'][str(pid)]['score'] == 1.0
    with pytest.raises(OperationFailure) as invalid:
        db.user_preference_scores.insert_one({'user_id': ObjectId()})
    assert invalid.value.code == 121
    with pytest.raises(DuplicateKeyError):
        db.user_preference_scores.insert_one({**second, '_id': ObjectId()})
    assert db.user_preference_scores.count_documents({}) == 1


def test_real_rerun_decays_product_preserves_cross_scores_and_rejects_older_time(score_db):
    db, uid, pid = score_db
    rebuild_member(db, uid, as_of=NOW, apply=True)
    cross = {str(ObjectId()): {'raw_score': 3.0, 'score': 2.0, 'last_event_at': NOW}}
    db.user_preference_scores.update_one({'user_id': uid}, {'$set': {'cross_category_scores': cross}})
    result = rebuild_member(db, uid, as_of=NOW+timedelta(days=30), apply=True)['snapshot']
    assert result['products'][str(pid)]['score'] == .5
    assert next(iter(result['major_categories'].values()))['score'] == 1.0
    assert result['cross_category_scores'][next(iter(cross))]['score'] == 2.0
    before = db.user_preference_scores.find_one({'user_id': uid})
    with pytest.raises(ScoreConflict):
        rebuild_member(db, uid, as_of=NOW, apply=True)
    assert db.user_preference_scores.find_one({'user_id': uid}) == before


def test_real_service_rejects_missing_member_unique_index(score_db):
    db, uid, _ = score_db
    db.user_preference_scores.drop_indexes()
    assert not rebuild_member(db, uid, as_of=NOW)['applied']
    with pytest.raises(ScoreError):
        rebuild_member(db, uid, as_of=NOW, apply=True)
    assert db.user_preference_scores.count_documents({}) == 0


def test_real_two_stale_preimages_have_only_one_cas_winner(score_db, monkeypatch):
    db, uid, _ = score_db
    rebuild_member(db, uid, as_of=NOW, apply=True)
    target, gate = db.user_preference_scores.full_name, Barrier(2)
    replace = Collection.replace_one
    def synchronized_replace(collection, query, replacement, *args, **kwargs):
        if collection.full_name == target:
            gate.wait(timeout=10)
        return replace(collection, query, replacement, *args, **kwargs)
    monkeypatch.setattr(Collection, 'replace_one', synchronized_replace)
    times = [NOW+timedelta(seconds=1), NOW+timedelta(seconds=2)]
    def attempt(as_of):
        try:
            rebuild_member(db, uid, as_of=as_of, apply=True)
            return 'written', as_of
        except ScoreConflict:
            return 'conflict', as_of
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, times))
    assert sorted(status for status, _ in results) == ['conflict', 'written']
    winner = next(as_of for status, as_of in results if status == 'written')
    assert utc(db.user_preference_scores.find_one({'user_id': uid})['updated_at']) == winner
    assert db.user_preference_scores.count_documents({}) == 1


def test_real_concurrent_creation_uses_unique_index_without_duplicate_snapshots(score_db, monkeypatch):
    db, uid, _ = score_db
    target, gate = db.user_preference_scores.full_name, Barrier(2)
    insert = Collection.insert_one
    def synchronized_insert(collection, document, *args, **kwargs):
        if collection.full_name == target:
            gate.wait(timeout=10)
        return insert(collection, document, *args, **kwargs)
    monkeypatch.setattr(Collection, 'insert_one', synchronized_insert)
    def attempt(offset):
        try:
            rebuild_member(db, uid, as_of=NOW+timedelta(seconds=offset), apply=True)
            return 'written'
        except ScoreConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (1, 2)))
    assert sorted(results) == ['conflict', 'written']
    assert db.user_preference_scores.count_documents({}) == 1


def test_real_full_preimage_detects_new_field_with_same_timestamp(score_db, monkeypatch):
    db, uid, _ = score_db
    rebuild_member(db, uid, as_of=NOW, apply=True)
    target = db.user_preference_scores.full_name
    replace = Collection.replace_one
    def competing_admin_write(collection, query, replacement, *args, **kwargs):
        if collection.full_name == target:
            # Deliberate privileged schema bypass, without changing updated_at:
            # a full preimage fence must not erase an unknown concurrent field.
            collection.update_one({'user_id': uid}, {'$set': {'concurrent_note': 'other-worker'}},
                                  bypass_document_validation=True)
        return replace(collection, query, replacement, *args, **kwargs)
    monkeypatch.setattr(Collection, 'replace_one', competing_admin_write)
    with pytest.raises(ScoreConflict):
        rebuild_member(db, uid, as_of=NOW+timedelta(seconds=1), apply=True)
    row = db.user_preference_scores.find_one({'user_id': uid})
    assert row['concurrent_note'] == 'other-worker' and utc(row['updated_at']) == NOW


def test_real_failed_atomic_replacement_keeps_complete_old_snapshot(score_db, monkeypatch):
    db, uid, _ = score_db
    rebuild_member(db, uid, as_of=NOW, apply=True)
    before = db.user_preference_scores.find_one({'user_id': uid})
    target = db.user_preference_scores.full_name
    replace = Collection.replace_one
    def invalid_replacement(collection, query, replacement, *args, **kwargs):
        if collection.full_name == target:
            replacement = {**replacement, 'schema_version': 3}
        return replace(collection, query, replacement, *args, **kwargs)
    monkeypatch.setattr(Collection, 'replace_one', invalid_replacement)
    with pytest.raises(OperationFailure) as rejected:
        rebuild_member(db, uid, as_of=NOW+timedelta(days=30), apply=True)
    assert rejected.value.code == 121
    assert db.user_preference_scores.find_one({'user_id': uid}) == before
    assert db.user_preference_scores.count_documents({}) == 1
