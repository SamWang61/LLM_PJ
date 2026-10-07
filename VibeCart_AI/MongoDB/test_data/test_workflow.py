"""Independent fixture invariants and intentional corruption rejection."""
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import pytest
from bson import json_util, Decimal128

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow import build, validate, expected, digest, age, BATCH, GROUPS
from schema_test_profile import SCHEMAS, BASE


@pytest.fixture(scope='module')
def sample():
    path = Path(__file__).resolve().parents[1]/'supermarket/catalog_v4.extjson'
    catalog = json_util.loads(path.read_text(encoding='utf-8'), json_options=json_util.JSONOptions(tz_aware=True))
    return catalog, build(catalog)


def test_reproducible(sample):
    catalog, data = sample
    assert digest(data) == digest(build(catalog))


def test_balanced_demographics(sample):
    _, data = sample
    rows = expected(data)['demographics']
    assert len(rows) == 60
    assert all(r['count'] == 10 for r in rows)


def test_monthly_and_demo_coverage(sample):
    _, data = sample
    metrics = expected(data)
    assert len(metrics['monthly']) == 34
    assert sum(r['orders'] for r in metrics['monthly'].values()) == 3000
    assert sum(r['valid_orders'] for r in metrics['monthly'].values()) == 1800
    assert metrics['excluded_demo_expected_orders'] == 0
    assert all(o['is_demo'] for o in data['orders'])
    assert '2024-02-29' in metrics['daily']
    assert all(d in metrics['daily'] for d in ('2024-12-31', '2025-01-01', '2025-12-31', '2026-01-01'))


@pytest.mark.parametrize('case', ['amount', 'reference', 'demo', 'chronology'])
def test_reject_corruption(sample, case):
    catalog, original = sample
    data = deepcopy(original)
    if case == 'amount':
        data['orders'][0]['total_amount'] = Decimal128('0.01')
    elif case == 'reference':
        data['order_items'][0]['user_id'] = data['users'][-1]['_id']
    elif case == 'demo':
        data['orders'][0]['is_demo'] = False
    else:
        data['orders'][0]['ordered_at'] = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        validate(data, catalog)


def test_schema_is_additive():
    for name in BASE:
        current = deepcopy(SCHEMAS[name])
        current['$jsonSchema']['properties'].pop('synthetic_batch_id', None)
        if name == 'users':
            current['$jsonSchema']['properties'].pop('demographics')
        assert current == BASE[name]


def test_metrics_ignore_input_order(sample):
    _, original = sample
    data = {n:list(reversed(v)) for n,v in original.items()}
    assert expected(data) == expected(original)
