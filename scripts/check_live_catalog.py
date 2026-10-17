"""Read-only comparison of Atlas v4 catalog with the public storefront."""
import argparse
import hashlib
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from dotenv import dotenv_values
from pymongo import MongoClient

SITE = 'https://vibecart-llmai.web.app'
MONGO_HOST = 'vibecart-ai-free.odqe25w.mongodb.net'


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.product_links = []
        self._in_products = False
        self._price = False
        self.price = []
        self.options = {}
        self._option_id = None
        self._option_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section' and attrs.get('id') == 'products':
            self._in_products = True
        if tag == 'a' and self._in_products:
            match = re.match(r'^/product/([0-9a-f]{24})(?:[?#]|$)', attrs.get('href', ''))
            if match and match.group(1) not in self.product_links:
                self.product_links.append(match.group(1))
        if tag == 'div' and 'detail-price' in attrs.get('class', '').split():
            self._price = True
        if tag == 'option' and re.fullmatch(r'[0-9a-f]{24}', attrs.get('value', '')):
            self._option_id = attrs['value']
            self._option_text = []

    def handle_endtag(self, tag):
        if tag == 'section':
            self._in_products = False
        if tag == 'div' and self._price:
            self._price = False
        if tag == 'option' and self._option_id:
            self.options[self._option_id] = ' '.join(self._option_text)
            self._option_id = None

    def handle_data(self, data):
        self.text.append(data)
        if self._price:
            self.price.append(data)
        if self._option_id:
            self._option_text.append(data)


def get_page(path):
    request = Request(SITE + path, headers={'User-Agent': 'LLM-PJ-SAM-readonly-catalog-audit/1'})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f'HTTP {response.status}')
        parser = Page()
        parser.feed(response.read().decode('utf-8'))
        return parser


def text_price(value):
    match = re.search(r'NT\$\s*([0-9,]+\.[0-9]{2})', value)
    return Decimal(match.group(1).replace(',', '')) if match else None


def check_detail(item):
    product, skus = item
    product_id = str(product['_id'])
    problems = []
    try:
        page = get_page('/product/' + product_id)
        available = [sku for sku in skus if sku['status'] == 'active']
        expected_price = min((sku['price'].to_decimal() for sku in available), default=Decimal('0'))
        expected_stock = sum(sku['available_quantity'] for sku in available)
        if text_price(' '.join(page.price)) != expected_price:
            problems.append('display_price')
        stock = re.search(r'現有庫存\s*[：:]\s*([0-9,]+)', ' '.join(page.text))
        if not stock or int(stock.group(1).replace(',', '')) != expected_stock:
            problems.append('display_stock')
        if set(page.options) != {str(sku['_id']) for sku in available}:
            problems.append('sku_options')
        for sku in available:
            label = page.options.get(str(sku['_id']), '')
            if (sku['sku_code'] not in label or
                    text_price(label) != sku['price'].to_decimal() or
                    not re.search(r'庫存\s*' + str(sku['available_quantity']) + r'(?!\d)', label)):
                problems.append('sku_price_or_stock')
                break
    except Exception as error:
        problems.append('request_or_parse_' + type(error).__name__)
    return {'product_id': product_id, 'issues': sorted(set(problems))} if problems else None


def run(db):
    products = list(db.products.find({'schema_version': 4, 'status': 'active'}).sort('_id', 1))
    ids = [item['_id'] for item in products]
    skus = list(db.product_skus.find({'product_id': {'$in': ids}, 'status': 'active'}))
    by_product = {}
    for sku in skus:
        by_product.setdefault(sku['product_id'], []).append(sku)
    expected_ids = [str(item['_id']) for item in products]
    pages = math.ceil(len(products) / 24)
    problems = []
    for number in range(1, pages + 1):
        try:
            page = get_page('/?' + urlencode({'page': number}))
            summary = re.search(r'共\s*(\d+)\s*項商品\s*·\s*第\s*(\d+)\s*/\s*(\d+)\s*頁',
                                ' '.join(page.text))
            if not summary or tuple(map(int, summary.groups())) != (len(products), number, pages):
                problems.append({'page': number, 'issue': 'pagination_summary'})
            if page.product_links != expected_ids[(number - 1) * 24:number * 24]:
                problems.append({'page': number, 'issue': 'product_links_or_order'})
        except Exception as error:
            problems.append({'page': number, 'issue': 'request_or_parse_' + type(error).__name__})
    search_issues = []
    probes = [products[index]['product_name'][:200] for index in (0, len(products) // 2, len(products) - 1)]
    probes.append('SAM-NO-MATCH-20261017')
    for query in probes:
        token = query.casefold()
        matches = []
        for product in products:
            variants = [' '.join(sku.get('variant_attributes', {}).values())
                        for sku in by_product.get(product['_id'], [])]
            text = ' '.join([product['product_name'], product.get('summary') or '', *variants]).casefold()
            if token in text:
                matches.append(str(product['_id']))
        fingerprint = hashlib.sha256(query.encode('utf-8')).hexdigest()[:12]
        try:
            page = get_page('/?' + urlencode({'q': query}))
            summary = re.search(r'共\s*(\d+)\s*項商品\s*·\s*第\s*(\d+)\s*/\s*(\d+)\s*頁',
                                ' '.join(page.text))
            if (not summary or tuple(map(int, summary.groups())) !=
                    (len(matches), 1, max(1, math.ceil(len(matches) / 24))) or
                    page.product_links != matches[:24]):
                search_issues.append({'query_sha256_prefix': fingerprint, 'issue': 'search_result_mismatch'})
        except Exception as error:
            search_issues.append({'query_sha256_prefix': fingerprint,
                                  'issue': 'request_or_parse_' + type(error).__name__})
    with ThreadPoolExecutor(max_workers=4) as pool:
        details = [result for result in pool.map(check_detail,
                   ((item, by_product.get(item['_id'], [])) for item in products)) if result]
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'mode': 'read_only',
            'source': 'Atlas active v4 products/SKUs and public Firebase Hosting HTML',
            'products': len(products), 'active_skus': len(skus), 'pages_checked': pages,
            'details_checked': len(products), 'searches_checked': len(probes),
            'listing_issues': problems, 'search_issues': search_issues, 'detail_issues': details,
            'status': 'passed' if not problems and not search_issues and not details else 'failed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    target = Path(args.report)
    if target.exists():
        raise ValueError('Choose a new report path')
    config = dotenv_values(args.env_file)
    if (urlparse(config.get('MONGO_URI', '')).hostname != MONGO_HOST or
            config.get('MONGO_DB') != 'vibecart_ai' or
            (config.get('DATA_MODE') or os.environ.get('DATA_MODE')) != 'v4'):
        raise ValueError('Unexpected database target')
    with MongoClient(config['MONGO_URI'], serverSelectionTimeoutMS=10000) as client:
        report = run(client['vibecart_ai'])
    with target.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'products', 'active_skus',
                                                   'pages_checked', 'details_checked', 'searches_checked')}))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'error', 'type': type(error).__name__}))
        raise SystemExit(2)
