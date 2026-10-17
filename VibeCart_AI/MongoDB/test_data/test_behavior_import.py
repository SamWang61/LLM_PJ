import sys
from copy import deepcopy
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from behavior_import import missing_rows, isolation_evidence, run
from behavior_fixture import BATCH
from bson import ObjectId


def test_idempotency_and_payload_conflict():
    event = {'_id': ObjectId(), 'event_id': 'synthetic:one', 'quantity': 1}
    assert missing_rows([event], []) == [event]
    assert missing_rows([event], [deepcopy(event)]) == []
    altered = {**event, 'quantity': 2}
    with pytest.raises(ValueError): missing_rows([event], [altered])
    with pytest.raises(ValueError): missing_rows([event], [{**event, '_id': ObjectId()}])
    with pytest.raises(ValueError): missing_rows([event], [{**event, 'event_id': 'other'}])
    with pytest.raises(ValueError): missing_rows([event], [event, event])


def test_apply_is_blocked_before_database_access():
    class Target:
        name = 'vibecart_ai'
    with pytest.raises(ValueError, match='isolation evidence'): run(Target(), 'apply')


def test_isolation_requires_every_consumer(tmp_path):
    import json
    from behavior_import import CONSUMERS
    path = tmp_path / 'evidence.json'
    commit = 'a' * 40
    value = {'database': 'vibecart_ai', 'batch': BATCH, 'deployment_ref': commit,
             'checked_at': '2026-10-17T00:00:00Z', 'consumer_checks': {k: {
                 'status': 'passed', 'source_commit': commit, 'image_digest': 'sha256:' + 'b' * 64,
                 'revision': 'test-only', 'remote_evidence_url': 'https://example.test/evidence',
                 'checked_at': '2026-10-17T00:00:00Z', 'synthetic_input_count': 1,
                 'synthetic_visible_count': 0, 'normal_visible_count': 1}
                 for k in CONSUMERS}}
    path.write_text(json.dumps(value), encoding='utf-8')
    assert isolation_evidence(path)
    value['consumer_checks']['admin_monitor'] = 'failed'
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError): isolation_evidence(path)
    value['consumer_checks']['admin_monitor'] = 'passed'
    with pytest.raises(ValueError): isolation_evidence(path)


def test_undeployed_consumers_need_scoped_inventory(tmp_path):
    import json
    from behavior_import import CONSUMERS, OPTIONAL_UNDEPLOYED
    path = tmp_path / 'inventory-evidence.json'
    commit = 'a' * 40
    passed = {'status': 'passed', 'source_commit': commit,
              'image_digest': 'sha256:' + 'b' * 64, 'revision': 'revision',
              'remote_evidence_url': 'https://example.test/remote-check',
              'checked_at': '2026-10-17T00:00:00Z', 'synthetic_input_count': 1,
              'synthetic_visible_count': 0, 'normal_visible_count': 1}
    absent = {'status': 'not_deployed', 'source_commit': commit,
              'project_id': 'vibecart-llmai',
              'inventory_evidence_url': 'https://example.test/cloud-inventory',
              'inventory_sha256': 'c' * 64,
              'inventory_scopes': ['cloud_run_services', 'cloud_run_jobs',
                                   'cloud_scheduler', 'cloud_functions', 'pubsub_subscriptions'],
              'checked_at': '2026-10-17T00:00:00Z'}
    value = {'database': 'vibecart_ai', 'batch': BATCH, 'deployment_ref': commit,
             'checked_at': '2026-10-17T00:00:00Z',
             'consumer_checks': {k: deepcopy(absent if k in OPTIONAL_UNDEPLOYED else passed)
                                 for k in CONSUMERS}}
    path.write_text(json.dumps(value), encoding='utf-8')
    assert isolation_evidence(path)
    value['consumer_checks']['admin_monitor'] = deepcopy(absent)
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='Undeployed consumer'): isolation_evidence(path)
    value['consumer_checks']['admin_monitor'] = deepcopy(passed)
    del value['consumer_checks']['scoring_scheduler']['inventory_sha256']
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='Undeployed consumer'): isolation_evidence(path)
