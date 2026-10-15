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
    value = {'database': 'vibecart_ai', 'batch': BATCH, 'deployment_ref': 'test-only',
             'checked_at': '2026-10-11', 'consumer_checks': {k: 'passed' for k in CONSUMERS}}
    path.write_text(json.dumps(value), encoding='utf-8')
    assert isolation_evidence(path)
    value['consumer_checks']['admin_monitor'] = 'failed'
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError): isolation_evidence(path)
