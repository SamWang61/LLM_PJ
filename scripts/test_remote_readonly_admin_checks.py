"""Safety boundaries and independent business arithmetic for the remote probe."""
from unittest.mock import MagicMock
from bs4 import BeautifulSoup
from bson import Decimal128
import pytest
import remote_readonly_admin_checks as probe


def test_enabled_or_missing_model_status_cannot_reach_preset_posts(monkeypatch):
    monkeypatch.setattr(probe, 'verify_scope', lambda _: None)
    db = MagicMock(); db.name = 'vibecart_acceptance_pr21'
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.text = '<section class="admin-status"><li>雲端 LLM<small>已設定</small></li></section>'
    with pytest.raises(RuntimeError, match='explicitly disabled'):
        probe.run(db, {'service_url':'https://unused.invalid'}, session, {})
    session.post.assert_not_called()
    with pytest.raises(RuntimeError): probe.disabled_model(BeautifulSoup('<p>未啟用</p>', 'html.parser'))


def test_production_database_is_rejected_before_any_http_or_collection_read(monkeypatch):
    monkeypatch.setattr(probe, 'verify_scope', lambda _: None)
    db = MagicMock(); db.name = 'vibecart_ai'; session = MagicMock()
    with pytest.raises(RuntimeError, match='database mismatch'):
        probe.run(db, {}, session, {})
    session.get.assert_not_called(); session.post.assert_not_called(); db.__getitem__.assert_not_called()


def test_independent_totals_ignore_unpaid_and_cancelled_and_preserve_null_average():
    db = MagicMock()
    db.orders.find.side_effect = [[{'payment_status':'paid','status':'pending','total_amount':Decimal128('10.10')},
        {'payment_status':'paid','status':'cancelled','total_amount':Decimal128('200.00')},
        {'payment_status':'unpaid','status':'pending','total_amount':Decimal128('300.00')}], []]
    payload = {'source':{'demo_filter':'exclude'},
        'current_range':{'start':'2026-10-18','end':'2026-10-18'},
        'comparison_range':{'start':'2026-10-17','end':'2026-10-17'},
        'totals':{'current':{'all_orders':3,'valid_orders':1,'revenue':'10.10','average_order_value':'10.10'},
                  'comparison':{'all_orders':0,'valid_orders':0,'revenue':'0.00','average_order_value':None}}}
    assert probe.totals_match(db, payload)['current']['revenue'] == '10.10'
    query = db.orders.find.call_args_list[0].args[0]
    assert query['is_demo'] == {'$ne':True}
    assert query['ordered_at']['$gte'].utcoffset().total_seconds() == 8*3600


def test_independent_totals_reject_ui_numbers_that_disagree():
    db = MagicMock(); db.orders.find.return_value = []
    payload = {'source':{'demo_filter':'all'},'current_range':{'start':'2026-10-18','end':'2026-10-18'},
               'totals':{'current':{'all_orders':1}}}
    with pytest.raises(RuntimeError, match='disagrees'): probe.totals_match(db, payload)
