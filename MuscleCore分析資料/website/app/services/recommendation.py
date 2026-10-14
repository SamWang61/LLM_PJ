from collections import Counter
from .behavior_scope import production_events


def recommend_products(products, events, limit=4):
    """Explainable, API-free baseline recommender for the course MVP."""
    category_weights = Counter()
    product_weights = Counter()
    action_weight = {"view": 1, "favorite": 3, "cart": 4, "purchase": 8}
    product_by_id = {str(p["_id"]): p for p in products}

    for event in production_events(events):
        weight = action_weight.get(event.get("event_type"), 1)
        pid = str(event.get("product_id", ""))
        product_weights[pid] += weight
        product = product_by_id.get(pid)
        if product:
            category_weights[product.get("category", "其他")] += weight

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

