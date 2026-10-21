"""Request-time 6+4 ranking. No fabricated reviews or statistical rule writes."""
from collections import Counter
from datetime import datetime, timezone
import math
import re

from .behavior_scope import personalization_events

WEIGHTS = {'PURCHASE': 4, 'ADD_TO_CART': 3, 'SEARCH': 2, 'PRODUCT_VIEW': 1}
HALF_LIVES = dict(zip(WEIGHTS, (365, 180, 90, 30)))


def age_days(value, now):
    if not isinstance(value, datetime):
        return None
    return max(0, (now - value.replace(tzinfo=value.tzinfo or timezone.utc)).total_seconds() / 86400)


def actual_rating(product):
    return product.get('rating_status') == 'ACTUAL' and product.get('rating_count', 0) > 0


def rating_key(product):
    if not actual_rating(product):
        return (0, 0, 0)
    return (float(product['average_rating_display']), float(product['average_rating_raw']), product['rating_count'])


BOX_PREFIX = re.compile(r'^\s*[\[【]\s*箱購\s*[\]】]\s*')
BOX_NOTE = re.compile(r'[(（][^()（）]*箱購[^()（）]*[)）]')
PACK_SUFFIX = re.compile(r'\s*[x×X*]\s*\d+(?:\s*[x×X*]\s*\d+)*\D*$')
UNIT_WORDS = re.compile(r'(?<=\d)\s*(kg|g|ml|l)\s*(?:公斤|公克|克|毫升|公升)', re.IGNORECASE)
# A dot between digits is part of capacity (1.5L differs from 15L), not decoration.
NOISE = re.compile(r'[\s\-_/·・,，。]+|(?<!\d)\.|\.(?!\d)')


def variant_key(name):
    """Same product in a different pack (single vs [箱購] case) maps to one key, so 6+4 shows it once."""
    text = BOX_NOTE.sub('', BOX_PREFIX.sub('', name or ''))
    text = PACK_SUFFIX.sub('', text)
    text = UNIT_WORDS.sub(lambda m: m.group(1), text)
    return NOISE.sub('', text).casefold()


def is_pack_variant(name):
    name = name or ''
    return bool(BOX_PREFIX.search(name) or BOX_NOTE.search(name) or PACK_SUFFIX.search(name))


def variant_tokens(product):
    """(token to record, tokens that conflict). Two plain items never merge; a pack variant merges with
    the plain item or another pack of the same key."""
    name = product.get('name') or product.get('product_name')
    key = variant_key(name)
    if is_pack_variant(name):
        return 'pack:' + key, {'pack:' + key, 'plain:' + key}
    return 'plain:' + key, {'pack:' + key}


def take_distinct(ranked, count, category_cap, excluded=()):
    """Keep the highest-ranked item per product and per pack variant; excluded holds product IDs and variant tokens."""
    seen, categories, result = set(excluded), Counter(), []
    for product, score, reason in ranked:
        pid, category = str(product['_id']), str(product['minor_category_id'])
        token, conflicts = variant_tokens(product)
        if pid in seen or seen & conflicts or categories[category] >= category_cap:
            continue
        seen.update((pid, token))
        categories[category] += 1
        result.append({'product': product, 'score': score, 'reason': reason})
        if len(result) == count:
            break
    return result


def recommendations_6_4(products, events, rules=(), settings=None, now=None, semantic_scores=None):
    settings = settings if isinstance(settings, dict) else {}
    now = now or datetime.now(timezone.utc)
    semantic_scores = semantic_scores or {}
    products = [p for p in products if p.get('status') == 'active'
                and p.get('is_ai_recommendable', False) and p.get('stock', 0) > 0]
    by_id = {str(p['_id']): p for p in products}
    major, minor, purchases = Counter(), Counter(), {}
    def values(name, defaults, minimum):
        raw = settings.get(name)
        raw = raw if isinstance(raw, dict) else {}
        return {key: raw[key] if isinstance(raw.get(key), (int, float)) and not isinstance(raw[key], bool)
                and math.isfinite(raw[key]) and raw[key] >= minimum else value for key, value in defaults.items()}
    weights = values('weights', WEIGHTS, 0)
    half_lives = values('half_life_days', HALF_LIVES, 1)
    for event in personalization_events(events):
        kind = event.get('event_type')
        age = age_days(event.get('event_at'), now)
        if kind not in WEIGHTS or age is None:
            continue
        product = by_id.get(str(event.get('product_id')))
        mid = event.get('major_category_id') or (product or {}).get('major_category_id')
        sid = event.get('minor_category_id') or (product or {}).get('minor_category_id')
        value = weights[kind] * 0.5 ** (age / half_lives[kind])
        if mid:
            major[str(mid)] += value
        if sid:
            minor[str(sid)] += value
        if kind == 'SEARCH' and not mid and not sid:
            query = (event.get('search_query') or '').strip().casefold()
            matches = [p for p in products if query and query in
                       ' '.join((p['name'], p.get('summary', ''), p.get('description', ''))).casefold()]
            for key in {str(p['major_category_id']) for p in matches}:
                major[key] += value
            for key in {str(p['minor_category_id']) for p in matches}:
                minor[key] += value
        if kind == 'PURCHASE' and product:
            pid = str(product['_id'])
            purchases[pid] = min(purchases.get(pid, age), age)
    primary = max(major, key=major.get) if major else None
    usable = []
    for product in products:
        age = purchases.get(str(product['_id']))
        if age is not None:
            interval = product.get('expected_repurchase_interval_days')
            if product.get('product_lifecycle_type') == 'durable' and age < 365:
                continue
            if product.get('product_lifecycle_type') == 'consumable' and (not interval or age < interval):
                continue
        usable.append(product)
    personalized = []
    for product in usable:
        mid, sid = str(product['major_category_id']), str(product['minor_category_id'])
        score = min(70, major[mid]) + min(30, minor[sid])
        # Cold-start browsing uses actual >=4.5; it is not a first-member snapshot.
        if not major and not minor and (not actual_rating(product) or rating_key(product)[0] < 4.5):
            continue
        reason = '依你的分類偏好推薦' if score else (
            '真實高星商品' if actual_rating(product) and rating_key(product)[0] >= 4.5 else '可售商品探索')
        personalized.append((product, score, reason))
    personalized.sort(key=lambda row: (-row[1], -semantic_scores.get(str(row[0]['_id']), 0),
                      *(-x for x in rating_key(row[0])), str(row[0]['_id'])))
    personal = take_distinct(personalized, 6, 3)
    selected = {str(item['product']['_id']) for item in personal}
    # Cross-category picks must not repeat a pack variant already shown in the personal block.
    shown_variants = {variant_tokens(item['product'])[0] for item in personal}
    cross = []
    for product in usable:
        if str(product['_id']) in selected or str(product['major_category_id']) == primary:
            continue
        if not actual_rating(product) or rating_key(product)[0] < 4.5:
            continue
        relation = 0
        for rule in rules:
            antecedent, consequent = rule['antecedent'], rule['consequent']
            if (not major[str(antecedent['major_category_id'])]
                    or not minor[str(antecedent['minor_category_id'])]
                    or consequent['major_category_id'] != product['major_category_id']
                    or consequent['minor_category_id'] != product['minor_category_id']):
                continue
            if (rule.get('status') != 'active'
                    or rule['antecedent_customer_count'] < max(rule['minimum_sample_size'], settings.get('cross_min_customers', 500))
                    or rule['co_purchase_count'] < settings.get('cross_min_co_purchases', 50)
                    or rule['confidence'] < settings.get('cross_min_confidence', .05)
                    or rule['lift'] < settings.get('cross_min_lift', 1.2)):
                continue
            relation = max(relation, rule['confidence'] * math.log1p(rule['lift']) * math.log1p(rule['co_purchase_count']))
        cross.append((product, relation, '跨類共購關聯・高星優先' if relation else '跨類高星探索'))
    # New policy: rating first, then sample size and validated association strength.
    cross.sort(key=lambda row: (*(-x for x in rating_key(row[0])), -row[1], str(row[0]['_id'])))
    return {'personalized': personal, 'cross_category': take_distinct(cross, 4, 2, selected | shown_variants),
            'source': 'rules-6plus4-rating-v1'}
