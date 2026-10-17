"""Exercise existing read-only admin routes on the private acceptance service.

Run only inside the transaction probe's registered fixture/cleanup scope. Never
enable a model, refresh vectors, call a management-write route or save raw pages.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from bs4 import BeautifulSoup
from remote_d4_consumer_probe import require, verify_scope

INTENTS = ('period_compare', 'replenishment', 'promotion', 'revenue_change')
READ_PATHS = ('/admin/', '/admin/recommendations', '/admin/ai/insight',
              '/admin/ai/recommendation', '/admin/ai/compare')
BUSINESS = ('products', 'product_skus', 'orders', 'order_items', 'users',
            'carts', 'cart_events', 'behavior_events')


def disabled_model(soup):
    lights = [row for row in soup.select('.admin-status li')
              if '雲端 LLM' in row.get_text(' ', strip=True)]
    require(lights and all(row.small and row.small.get_text(strip=True) == '未啟用'
                           for row in lights), 'Cloud LLM must be explicitly disabled before preset POST')


def totals_match(db, payload):
    """Independent date/demo/paid/cancelled calculation; no application import."""
    tz = timezone(timedelta(hours=8))
    demo = payload['source']['demo_filter']
    require(demo in ('all', 'exclude', 'only'), 'Unexpected demo filter')
    checked = {}
    for period in ('current', 'comparison'):
        limits = payload[period+'_range']
        after = datetime.fromisoformat(limits['start']).replace(tzinfo=tz)
        before = datetime.fromisoformat(limits['end']).replace(tzinfo=tz)+timedelta(days=1)
        query = {'ordered_at': {'$gte': after, '$lt': before}}
        if demo != 'all': query['is_demo'] = True if demo == 'only' else {'$ne': True}
        orders = list(db.orders.find(query, {'payment_status': 1, 'status': 1, 'total_amount': 1}))
        valid = [o for o in orders if o.get('payment_status') == 'paid' and o.get('status') != 'cancelled']
        amounts = [o['total_amount'].to_decimal() if hasattr(o['total_amount'], 'to_decimal')
                   else Decimal(str(o['total_amount'])) for o in valid]
        revenue = sum(amounts, Decimal('0')).quantize(Decimal('.01'))
        expected = {'all_orders': len(orders), 'valid_orders': len(valid),
                    'revenue': str(revenue),
                    'average_order_value': str((revenue/len(valid)).quantize(Decimal('.01'))) if valid else None}
        require(payload['totals'][period] == expected, 'Admin aggregate disagrees with independent Atlas calculation')
        checked[period] = expected
    return checked


def run(db, config, admin, report):
    verify_scope(config)
    require(db.name == 'vibecart_acceptance_pr21', 'Admin probe database mismatch')
    base = config['service_url'].rstrip('/')
    before = {name: db[name].count_documents({}) for name in BUSINESS}
    pages = {}
    for path in READ_PATHS:
        response = admin.get(base+path, allow_redirects=False, timeout=30)
        require(response.status_code == 200, 'Read-only admin route unavailable: '+path)
        pages[path] = BeautifulSoup(response.text, 'html.parser')
    dashboard = pages['/admin/']
    disabled_model(dashboard)
    closed = dashboard.select('.admin-nav-disabled[aria-disabled="true"]')
    require(len(closed) == 3 and all('尚未開放' in row.get_text() for row in closed),
            'D5 management navigation must remain disabled')
    insight = pages['/admin/ai/insight']
    disabled_model(insight)
    require(not insight.select('textarea[name="question"]'), 'Free question unexpectedly exposed')
    form = insight.select_one('form.ask-form')
    require(form is not None, 'Fixed-question form missing')
    fields = {e['name']: e.get('value', '') for e in form.select('input[name]')}
    require(fields.get('csrf_token') and fields.get('start') and fields.get('end'), 'Preset form contract missing')
    buttons = [e.get('value') for e in form.select('button[name="intent"]')]
    require(tuple(buttons) == INTENTS, 'Unexpected fixed-question contract')
    results = []
    for demo in ('all', 'exclude', 'only'):
        for intent in INTENTS:
            response = admin.post(base+'/admin/ai/insight', data={**fields, 'demo': demo,
                'intent': intent, 'question': 'qa-preset-ignore@example.invalid'},
                allow_redirects=False, timeout=30)
            require(response.status_code == 200, 'Fixed-question response failed')
            answer = BeautifulSoup(response.text, 'html.parser')
            disabled_model(answer)
            require(answer.select_one('.ai-answer') and '規則計算，非 AI 分析' in answer.get_text(),
                    'Fixed-question response is not explicitly rules-only')
            preview = answer.select_one('.payload-preview')
            require(preview and '未送出' in preview.summary.get_text(), 'Preset indicates external model transmission')
            request = json.loads(preview.select_one('code').get_text())
            require(request['intent'] == intent and request['untrusted_question'] is None,
                    'Preset forwarded untrusted free text')
            require('qa-preset-ignore@example.invalid' not in json.dumps(request), 'Preset leaked free text')
            data = request['data']
            require(data['contract_version'] == 'ai-whitelist-v1' and data['source']['demo_filter'] == demo,
                    'Whitelist or demo selection drifted')
            actual = totals_match(db, data)
            results.append({'intent': intent, 'demo': demo, 'http': 200,
                            'rules_only': True, 'free_text_ignored': True, 'independent_totals': actual})
    invalid = admin.get(base+'/admin/ai/insight', params={'start':'2026-10-18','end':'2026-10-01'},
                        allow_redirects=False, timeout=30)
    require(invalid.status_code == 400, 'Invalid date range accepted')
    unknown = admin.post(base+'/admin/ai/insight', data={**fields,'intent':'not-an-intent'},
                         allow_redirects=False, timeout=30)
    require(unknown.status_code == 400, 'Unknown intent accepted')
    forged = admin.post(base+'/admin/ai/insight', data={**fields,'intent':'free_question',
                        'question':'測試目前未開放的入口'}, allow_redirects=False, timeout=30)
    require(forged.status_code == 403, 'Disabled free-question POST accepted')
    after = {name: db[name].count_documents({}) for name in BUSINESS}
    require(before == after, 'Read-only admin checks changed business collection counts')
    report['readonly_admin'] = {'get_routes': list(READ_PATHS), 'get_http': 200,
        'fixed_questions': results, 'invalid_range_http': 400, 'unknown_intent_http': 400,
        'disabled_free_question_http': 403, 'disabled_d5_links': 3,
        'business_counts_before': before, 'business_counts_after': after,
        'model_enabled': False, 'vector_refresh_tested': False,
        'browser_or_human_acceptance': False}
