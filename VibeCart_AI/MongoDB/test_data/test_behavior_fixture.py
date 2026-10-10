import sys
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import pytest
from bson import json_util

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow import build as source_build, digest
from behavior_fixture import build, validate, expected
from schema_complete_v4 import SCHEMAS


@pytest.fixture(scope='module')
def sample():
    catalog = json_util.loads((Path(__file__).resolve().parents[1] / 'supermarket/catalog_v4.extjson').read_text(encoding='utf-8'),
                              json_options=json_util.JSONOptions(tz_aware=True))
    data = source_build(catalog)
    return data, catalog, build(data, catalog)


def test_reproducible_and_no_source_mutation(sample):
    data, catalog, events = sample
    before = digest([data, catalog])
    shuffled = {k: list(reversed(v)) for k, v in data.items()}
    assert digest(events) == digest(build(shuffled, catalog))
    assert before == digest([data, catalog])
    metrics = expected(events)
    assert len(set(metrics['counts'].values())) == 1
    assert metrics['weighted_event_count'] == len(events) // 4 * 10
    assert metrics['production_attribution_events'] == 0
    props = SCHEMAS['behavior_events']['$jsonSchema']
    assert all(set(e) == set(props['required']) for e in events)


@pytest.mark.parametrize('case', ['duplicate', 'isolation', 'order', 'user', 'quantity', 'time', 'processed', 'search', 'category'])
def test_reject_corruption(sample, case):
    data, catalog, original = sample
    events = deepcopy(original)
    purchase = next(e for e in events if e['event_type'] == 'PURCHASE')
    if case == 'duplicate': events.append(deepcopy(events[0]))
    elif case == 'isolation': events[0]['metadata']['synthetic'] = False
    elif case == 'order': purchase['order_id'] = None
    elif case == 'user': purchase['user_id'] = data['users'][-1]['_id']
    elif case == 'quantity': purchase['quantity'] += 1
    elif case == 'time': purchase['event_at'] -= timedelta(days=10000)
    elif case == 'processed': purchase['processed_at'] = purchase['event_at']
    elif case == 'search': next(e for e in events if e['event_type'] == 'SEARCH')['search_query'] = ''
    else: events[0]['major_category_id'] = None
    with pytest.raises(ValueError): validate(events, data, catalog)


@pytest.mark.parametrize('limit', [0, 1001, True, 1.5])
def test_order_limit(sample, limit):
    with pytest.raises(ValueError): build(sample[0], sample[1], limit)
