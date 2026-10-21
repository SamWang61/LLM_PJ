"""Recommendation attribution: impressions, clicks, add-to-cart and purchases in recommendation_logs.

Only signed-in members are logged (the schema requires user_id). Demo checkouts never count as
purchases, matching the production/attribution scope; synthetic test runs are not logged at all
because the recommendation_logs schema has no metadata field to mark them.
"""
import re
from datetime import timedelta
from uuid import uuid4
from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app
from ..db import utcnow

TYPES = {"personalized": "PERSONALIZED", "cross_category": "CROSS_CATEGORY"}
REASON_CODES = {"依你的分類偏好推薦": "CATEGORY_PREFERENCE", "真實高星商品": "HIGH_RATING", "可售商品探索": "EXPLORE",
                "跨類共購關聯・高星優先": "CO_PURCHASE", "跨類高星探索": "CROSS_HIGH_RATING"}
# Re-rendering the same list (tab refocus, fragment refresh) within this window is not a new impression.
DEDUPE_MINUTES = 30
PURCHASE_WINDOW_DAYS = 30
REC_ID = re.compile(r"^[0-9a-f]{32}$")


def logging_enabled():
    config = current_app.config
    return (config.get("DATA_MODE") == "v4" and not config.get("BEHAVIOR_SYNTHETIC_BATCH")
            and not config.get("CLOUD_PREVIEW_READ_ONLY"))


def valid_rec_id(value):
    return value if isinstance(value, str) and REC_ID.match(value) else None


def as_oid(value):
    try:
        return value if isinstance(value, ObjectId) else ObjectId(value)
    except (InvalidId, TypeError):
        return None


def log_impressions(db, member, result):
    """Write one log per non-empty block and return {block: recommendation_id} for link tagging."""
    if not member or not logging_enabled():
        return {}
    now = utcnow()
    ids = {}
    for block, kind in TYPES.items():
        entries = result.get(block) or []
        items = [{"product_id": as_oid(e["product"]["_id"]), "position": index, "score": float(max(0, e.get("score") or 0)),
                  "reason_code": REASON_CODES.get(e.get("reason"), "OTHER")} for index, e in enumerate(entries, 1)]
        items = [item for item in items if item["product_id"]]
        if not items:
            continue
        product_ids = [item["product_id"] for item in items]
        recent = db.recommendation_logs.find_one(
            {"user_id": member["_id"], "recommendation_type": kind,
             "shown_at": {"$gte": now - timedelta(minutes=DEDUPE_MINUTES)},
             "$expr": {"$eq": ["$items.product_id", product_ids]}},
            {"recommendation_id": 1, "items.product_id": 1}, sort=[("shown_at", -1)])
        if recent and [item["product_id"] for item in recent.get("items", [])] == product_ids:
            ids[block] = recent["recommendation_id"]
            continue
        rec_id = uuid4().hex
        db.recommendation_logs.insert_one({
            "schema_version": 4, "user_id": member["_id"], "recommendation_id": rec_id, "recommendation_type": kind,
            "algorithm_version": str(result.get("source") or "unknown")[:100], "items": items, "shown_at": now,
            "clicked_product_ids": [], "added_to_cart_product_ids": [], "purchased_product_ids": [], "created_at": now})
        ids[block] = rec_id
    return ids


def _mark(db, member, rec_id, product_id, field):
    """Add product_id to field only when the log belongs to this member and listed that product."""
    rec_id, pid = valid_rec_id(rec_id), as_oid(product_id)
    if not member or not rec_id or not pid or not logging_enabled():
        return False
    result = db.recommendation_logs.update_one(
        {"recommendation_id": rec_id, "user_id": member["_id"], "items.product_id": pid},
        {"$addToSet": {field: pid}})
    return result.matched_count == 1


def record_click(db, member, rec_id, product_id):
    return _mark(db, member, rec_id, product_id, "clicked_product_ids")


def record_add_to_cart(db, member, rec_id, product_id):
    return _mark(db, member, rec_id, product_id, "added_to_cart_product_ids")


def record_purchases(db, member, order, product_ids):
    """Credit recent logs where the member added the product to the cart; demo orders never count."""
    if not member or order.get("is_demo") or not logging_enabled():
        return 0
    since = utcnow() - timedelta(days=PURCHASE_WINDOW_DAYS)
    credited = 0
    for pid in {as_oid(p) for p in product_ids} - {None}:
        credited += db.recommendation_logs.update_many(
            {"user_id": member["_id"], "shown_at": {"$gte": since}, "added_to_cart_product_ids": pid},
            {"$addToSet": {"purchased_product_ids": pid}}).modified_count
    return credited


def record_order_purchases(db, member, order):
    """Keep all optional attribution reads inside the caller's best-effort boundary."""
    if not member or order.get("is_demo") or not logging_enabled():
        return 0
    product_ids = [line["product_id"] for line in db.order_items.find(
        {"order_id": order["_id"]}, {"product_id": 1})]
    return record_purchases(db, member, order, product_ids)


def recommendation_metrics(db, days=30):
    """Per-type funnel for the monitor page; rates are null when there is nothing to divide by."""
    since = utcnow() - timedelta(days=days)
    rows = []
    for kind, label in (("PERSONALIZED", "依你的喜好（6）"), ("CROSS_CATEGORY", "破圈推薦（4）")):
        stats = {"lists": 0, "impressions": 0, "clicks": 0, "added": 0, "purchased": 0}
        for log in db.recommendation_logs.find({"recommendation_type": kind, "shown_at": {"$gte": since}},
                                               {"items": 1, "clicked_product_ids": 1, "added_to_cart_product_ids": 1,
                                                "purchased_product_ids": 1}):
            stats["lists"] += 1
            stats["impressions"] += len(log.get("items", []))
            stats["clicks"] += len(log.get("clicked_product_ids", []))
            stats["added"] += len(log.get("added_to_cart_product_ids", []))
            stats["purchased"] += len(log.get("purchased_product_ids", []))
        ctr = stats["clicks"] / stats["impressions"] * 100 if stats["impressions"] else None
        cart_rate = stats["added"] / stats["clicks"] * 100 if stats["clicks"] else None
        rows.append({"type": kind, "label": label, **stats, "ctr": ctr, "cart_rate": cart_rate})
    return {"days": days, "rows": rows}
