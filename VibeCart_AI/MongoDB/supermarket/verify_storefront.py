"""Read-only integration smoke check: real Atlas + existing Flask v4 routes."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(REPO / 'MuscleCore分析資料' / 'website'))
from bootstrap_schema import connect, HOST
from app import create_app
from app.services.sku_gateway import catalog


def main():
    config = dotenv_values(ROOT.parent / '.env')
    assert urlparse(config['MONGO_URI']).hostname == HOST
    source = json.loads((ROOT / 'source_catalog.json').read_text(encoding='utf-8'))
    app = create_app({'TESTING': True, 'SECRET_KEY': 'read-only-smoke-no-login',
        'DATA_MODE': 'v4', 'MONGO_URI': config['MONGO_URI'], 'MONGO_DB': 'vibecart_ai',
        'ENABLE_CHECKOUT': False, 'AI_RECOMMENDATIONS_ENABLED': False, 'AI_SUMMARY_ENABLED': False})
    client = app.test_client()
    # First request uses Flask's unmodified get_db() and the real Atlas URI.
    first = client.get('/')
    assert first.status_code == 200 and 'VibeCart 超級市場' in first.text
    from flask import g
    with connect('.env') as mongo:
        db = mongo.vibecart_ai
        counts = {n: db[n].count_documents({}) for n in db.list_collection_names()}
        # Reuse the same live client for the remaining read-only route checks.
        app.before_request_funcs.setdefault(None, []).append(lambda: setattr(g, 'db', db))
        products = catalog(db)
        imported = [p for p in products if p['product_code'].startswith('CF-')]
        assert len(imported) >= len(source['items']) >= 300
        expected = {str(p['_id']) for p in products}
        seen = set()
        pages = (len(products) + 23) // 24
        for page in range(1, pages + 1):
            response = client.get('/', query_string={'page': page})
            assert response.status_code == 200
            found = re.findall(r'<article class="product-card"><a class="product-visual" href="/product/([a-f0-9]+)"', response.text)
            assert len(found) <= 24 and not seen.intersection(found)
            seen.update(found)
        assert seen == expected
        detail_checks = 0
        majors = sorted({p['major_category'] for p in imported})
        minors = sorted({p['category'] for p in imported})
        for major in majors:
            response = client.get('/', query_string={'major': major})
            assert response.status_code == 200
            assert f"共 {sum(p['major_category'] == major for p in products)} 項商品" in response.text
        for minor in minors:
            response = client.get('/', query_string={'category': minor})
            assert response.status_code == 200
            assert f"共 {sum(p['category'] == minor for p in products)} 項商品" in response.text
            p = next(p for p in imported if p['category'] == minor)
            response = client.get(f'/product/{p["_id"]}')
            assert response.status_code == 200 and '原商品頁' in response.text
            assert p['source_url'] in response.text and p['image_urls'][0] in response.text
            assert '選擇規格' in response.text or '規格' in response.text
            detail_checks += 1
        row = source['items'][-1]
        response = client.get('/', query_string={'q': row['name']})
        assert response.status_code == 200 and '共 1 項商品' in response.text
        assert counts == {n: db[n].count_documents({}) for n in db.list_collection_names()}
        report = {'checked_at': datetime.now(timezone.utc).isoformat(),
            'mode': 'Flask test client with real Atlas, anonymous read-only',
            'products_accessible': len(imported), 'pages_checked': pages,
            'major_filters_checked': len(majors), 'minor_filters_checked': len(minors),
            'detail_pages_checked': detail_checks, 'keyword_search': 'passed',
            'writes': 0, 'public_hosted_url': None,
            'limitation': 'Hosted deployment not verified; no public storefront URL supplied.'}
        (ROOT / 'storefront_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
