"""Read-event writer; mutation events remain inside the cart transaction."""
from uuid import uuid4
from flask import current_app, session
from ..db import get_db, utcnow


def behavior_metadata(*, legacy_default=False):
    batch = current_app.config.get("BEHAVIOR_SYNTHETIC_BATCH") or (
        "legacy-demo" if legacy_default else ""
    )
    return ({"synthetic": True, "synthetic_batch_id": batch,
             "exclude_from_attribution": True} if batch else {})


def record_read_event(user, kind, *, product=None, query=None):
    now = utcnow()
    product = product or {}
    get_db().behavior_events.insert_one({"schema_version": 4, "event_id": "read:" + str(uuid4()),
        "user_id": user["_id"], "anonymous_id": None,
        "session_id": session.setdefault("event_session", str(uuid4())), "event_type": kind,
        "product_id": product.get("_id"), "major_category_id": product.get("major_category_id"),
        "minor_category_id": product.get("minor_category_id"), "quantity": 1,
        "order_id": None, "cart_id": None, "search_query": query, "source": "organic",
        "recommendation_id": None, "event_at": now, "score_version": 1,
        "processed_at": None, "metadata": behavior_metadata(), "created_at": now})
