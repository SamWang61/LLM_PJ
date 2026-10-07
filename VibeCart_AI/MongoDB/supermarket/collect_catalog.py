"""Collect factual public catalog metadata, not retailer descriptions or image files.

Run with Python + requests + beautifulsoup4. Resume via detail_cache.json.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
BASE = 'https://online.uni-prosperity.com.tw'
GROUPS = [
    ('DAIRY', '乳品與蛋品', '生鮮冷凍', '鮮乳．調味乳'),
    ('DAIRY', '乳品與蛋品', '生鮮冷凍', '優酪乳．優格'),
    ('DAIRY', '乳品與蛋品', '生鮮冷凍', '雞蛋．豆製品'),
    ('FROZEN', '冷凍與冷藏食品', '生鮮冷凍', '水餃 麵食'),
    ('FROZEN', '冷凍與冷藏食品', '生鮮冷凍', '冰淇淋 雪糕'),
    ('FROZEN', '冷凍與冷藏食品', '生鮮冷凍', '包子饅頭 餡餅'),
    ('DRINK', '飲料與飲用水', '飲料零食', '礦泉水'),
    ('DRINK', '飲料與飲用水', '飲料零食', '綠茶．烏龍茶．其他茶飲'),
    ('DRINK', '飲料與飲用水', '飲料零食', '蔬果汁'),
    ('SNACK', '餅乾與休閒零食', '飲料零食', '鹹餅乾'),
    ('SNACK', '餅乾與休閒零食', '飲料零食', '甜餅乾'),
    ('SNACK', '餅乾與休閒零食', '飲料零食', '堅果類'),
    ('GROCERY', '米麵與食用油', '米油沖泡', '米'),
    ('GROCERY', '米麵與食用油', '米油沖泡', '泡麵'),
    ('GROCERY', '米麵與食用油', '米油沖泡', '食用油'),
    ('PANTRY', '調味與沖泡食品', '米油沖泡', '罐頭'),
    ('PANTRY', '調味與沖泡食品', '米油沖泡', '調味品'),
    ('PANTRY', '調味與沖泡食品', '米油沖泡', '茶包'),
    ('HOME', '家庭清潔與紙品', '日用生活', '抽取式．平板．滾筒'),
    ('HOME', '家庭清潔與紙品', '日用生活', '洗衣精 洗衣球'),
    ('HOME', '家庭清潔與紙品', '日用生活', '洗碗精'),
    ('CARE', '個人清潔與護理', '美妝個清', '口腔清潔用品'),
    ('CARE', '個人清潔與護理', '美妝個清', '沐浴用品'),
    ('CARE', '個人清潔與護理', '美妝個清', '洗護造型'),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def get_soup(url):
    # Three workers maximum; no login, proxy rotation or challenge bypass.
    time.sleep(0.25)
    r = requests.get(url, timeout=35, headers={'User-Agent': 'VibeCartClassroomCatalog/1.0'})
    r.raise_for_status()
    if urlparse(r.url).hostname != urlparse(BASE).hostname:
        raise ValueError('Unexpected redirect host')
    return BeautifulSoup(r.content.decode('utf-8'), 'html.parser'), r.url


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def detail(row):
    s, actual_url = get_soup(row['source_url'])
    product = None
    for script in s.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict) and obj.get('@type') == 'Product':
            product = obj
            break
    if not product or str(product.get('sku')) != row['source_id']:
        raise ValueError('Product page does not match listing')
    # Do not save source description HTML, reviews, or tracking data.
    images = product.get('image', [])
    if isinstance(images, str):
        images = [images]
    image = next((u for u in images if u.startswith(BASE + '/')), None)
    if not image:
        raise ValueError('No first-party product image')
    response = requests.head(image, timeout=25)
    response.raise_for_status()
    if not response.headers.get('Content-Type', '').startswith('image/'):
        raise ValueError('Image response is not an image')
    offer = product.get('offers', {})
    if offer.get('priceCurrency') != 'TWD' or float(offer.get('price', 0)) <= 0:
        raise ValueError('Missing TWD price')
    brand = product.get('brand')
    if isinstance(brand, dict):
        brand = brand.get('name')
    row = dict(row, name=product['name'], source_url=actual_url,
               source_price_twd=str(offer['price']), image_url=image,
               brand=brand or row.get('brand'), fetched_at=now(),
               image_checked_at=now(), image_http_status=response.status_code)
    return row


def main():
    home, homepage_url = get_soup('https://online.carrefour.com.tw/zh/homepage/')
    cache_path = ROOT / 'detail_cache.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    selected = []
    seen = set()
    failures = []
    for i, (major_code, major, section, minor) in enumerate(GROUPS, 1):
        link = next(a['href'] for a in home.select('a[href]')
                    if a.get_text(strip=True) == minor and unquote(a['href']).startswith('/zh/' + section + '/'))
        listing_url = urljoin(BASE, link)
        soup, _ = get_soup(listing_url)
        candidates = {}
        for a in soup.select('a[data-pid][data-variant]'):
            pid = a['data-pid']
            spec = a.get('data-variant', '').strip()
            if pid in seen or not spec or len(spec) > 100 or not pid.isdigit():
                continue
            # Keep only this category's tiles, not suggested items elsewhere on the page.
            if minor not in a.get('data-category', '').split('/'):
                continue
            brand = a.get('data-brand')
            candidates[pid] = {'source_id': pid, 'name': a['data-name'],
                'source_url': urljoin(BASE, a['href']), 'listing_url': listing_url,
                'source_category': a['data-category'], 'specification': spec,
                'brand': None if brand in ('null', '', None) else brand,
                'major_code': major_code, 'major_category': major,
                'minor_code': f'{major_code}-{i:02d}', 'minor_category': minor}
        valid = []
        pending = []
        for pid, row in list(candidates.items())[:24]:
            if pid in cache:
                valid.append({**cache[pid], **{k: row[k] for k in ('major_code', 'major_category', 'minor_code', 'minor_category')}})
            else:
                pending.append(row)
        pending = pending[:max(0, 16 - len(valid))]
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(detail, row): row for row in pending}
            for future in as_completed(futures):
                row = futures[future]
                try:
                    result = future.result()
                    cache[row['source_id']] = result
                    valid.append(result)
                    save(cache_path, cache)
                except Exception as exc:
                    failures.append({'source_id': row['source_id'], 'error_type': type(exc).__name__})
        valid.sort(key=lambda r: list(candidates).index(r['source_id']))
        picked = valid[:14]
        selected.extend(picked)
        seen.update(r['source_id'] for r in picked)
        print(f'{i:02d}/24 {major} / {minor}: {len(picked)}; total={len(selected)}', flush=True)
        save(ROOT / 'source_catalog.json', {'collected_at': now(), 'requested_homepage':
            'https://online.carrefour.com.tw/zh/homepage/', 'resolved_homepage': homepage_url,
            'description_policy': 'original testing summaries; no copied retailer descriptions',
            'image_policy': 'source URLs only; no image files copied',
            'items': selected, 'fetch_failures': failures})
    if len(selected) < 300:
        raise RuntimeError(f'Only {len(selected)} verified products; minimum is 300')
    print(f'COMPLETE {len(selected)} unique product pages, {len(GROUPS)} minor categories', flush=True)


if __name__ == '__main__':
    main()
