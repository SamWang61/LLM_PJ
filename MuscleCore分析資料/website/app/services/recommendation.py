from collections import Counter
import math
from .behavior_scope import production_events

# v4 recommendation_policy defaults (system_configs); the stored policy overrides them.
DEFAULT_WEIGHTS = {"PURCHASE": 4, "ADD_TO_CART": 3, "SEARCH": 2, "PRODUCT_VIEW": 1}
# Legacy storefront event names map onto the v4 vocabulary; favorite has no v4 event and counts like a cart add.
LEGACY_EVENT_TYPES = {"view": "PRODUCT_VIEW", "cart": "ADD_TO_CART", "favorite": "ADD_TO_CART",
                      "purchase": "PURCHASE", "search": "SEARCH"}


def policy_weights(db):
    """Read the active v4 policy weights, falling back to the defaults for missing or invalid values."""
    policy = db.system_configs.find_one({"config_key": "recommendation_policy", "status": "active"}) or {}
    settings = policy.get("settings")
    stored = settings.get("weights") if isinstance(settings, dict) else None
    if not isinstance(stored, dict):
        stored = {}
    weights = dict(DEFAULT_WEIGHTS)
    for event_type, value in stored.items():
        if (event_type in weights and isinstance(value, (int, float)) and not isinstance(value, bool)
                and value >= 0 and (not isinstance(value, float) or math.isfinite(value))):
            weights[event_type] = value
    return weights


def event_type(event):
    raw = event.get("event_type")
    return LEGACY_EVENT_TYPES.get(raw, raw)


def search_matches(product, query):
    query = (query or "").strip().lower()
    return bool(query) and query in f"{product.get('name', '')} {product.get('category', '')}".lower()


def recommend_products(products, events, limit=4, weights=None):
    """Explainable, API-free baseline recommender for the course MVP."""
    weights = weights or DEFAULT_WEIGHTS
    category_weights = Counter()
    product_weights = Counter()
    product_by_id = {str(p["_id"]): p for p in products}

    def add(product, weight):
        product_weights[str(product["_id"])] += weight
        category_weights[product.get("category", "其他")] += weight

    for event in production_events(events):
        kind = event_type(event)
        weight = weights.get(kind, 0)
        if not weight:
            continue
        if kind == "SEARCH":
            # SEARCH events carry a query instead of a product; credit the products it matches.
            for product in products:
                if search_matches(product, event.get("search_query")):
                    add(product, weight)
            continue
        product = product_by_id.get(str(event.get("product_id", "")))
        if product:
            add(product, weight)

    scored = []
    for product in products:
        pid = str(product["_id"])
        score = category_weights[product.get("category", "其他")] * 2
        score += product_weights[pid]
        score += float(product.get("rating", 0))
        score += min(int(product.get("sales_count", 0)) / 100, 5)
        reasons = []
        if category_weights[product.get("category", "其他")]:
            reasons.append(f"你常關注{product['category']}")
        if product.get("rating", 0) >= 4.7:
            reasons.append("高評價商品")
        if not reasons:
            reasons.append("本週熱門")
        scored.append((score, product, "、".join(reasons[:2])))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"product": item[1], "reason": item[2], "score": round(item[0], 1)} for item in scored[:limit]]

