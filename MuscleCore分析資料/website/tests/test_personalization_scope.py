"""B2: a real member's demo checkout shapes their recommendations but never counts as attribution."""
from datetime import datetime, timedelta, timezone
import mongomock
import pytest
from test_v4_routes import shop
from app.services.behavior_scope import (personalization_behavior_query, personalization_events,
                                         production_behavior_query, production_events)
from app.services.dashboard import recommendation_monitor

DEMO = {"demo_checkout": True, "exclude_from_attribution": True}


@pytest.mark.parametrize("metadata,personal,production", [
    ({}, True, True),
    (DEMO, True, False),
    ({"synthetic": True}, False, False),
    ({"synthetic_batch_id": "batch-1"}, False, False),
    ({"synthetic": True, "synthetic_batch_id": "batch-1", "exclude_from_attribution": True}, False, False),
])
def test_scopes_in_database_and_memory(metadata, personal, production):
    db = mongomock.MongoClient().scope
    db.behavior_events.insert_one({"event_type": "PURCHASE", "metadata": metadata})
    assert bool(list(db.behavior_events.find(personalization_behavior_query()))) is personal
    assert bool(list(personalization_events([{"metadata": metadata}]))) is personal
    assert bool(list(db.behavior_events.find(production_behavior_query()))) is production
    assert bool(list(production_events([{"metadata": metadata}]))) is production


def test_storefront_learns_from_demo_checkout_not_synthetic(shop, monkeypatch):
    _, client, db, uid, pid, _ = shop
    now = datetime.now(timezone.utc)
    db.behavior_events.insert_one({"user_id": uid, "product_id": pid, "event_type": "PURCHASE", "event_at": now, "metadata": DEMO})
    db.behavior_events.insert_many([{"user_id": uid, "product_id": pid, "event_type": "PURCHASE",
        "event_at": now + timedelta(seconds=1), "metadata": {"synthetic": True}} for _ in range(60)])
    seen = []
    def inspect(products, events, query):
        seen.extend(events)
        return {"items": [], "source": "rules"}
    monkeypatch.setattr("app.store_v4.storefront_recommendations", inspect)
    assert client.get("/").status_code == 200
    assert len(seen) == 1 and seen[0]["metadata"] == DEMO


def test_monitor_still_excludes_demo_checkout(shop):
    _, _, db, uid, pid, _ = shop
    now = datetime.now(timezone.utc)
    db.behavior_events.insert_many([
        {"user_id": uid, "product_id": pid, "event_type": "PURCHASE", "event_at": now, "metadata": DEMO},
        {"user_id": uid, "product_id": pid, "event_type": "PRODUCT_VIEW", "event_at": now, "metadata": {}}])
    result = recommendation_monitor(db, "v4")
    assert result["event_count"] == 1 and result["stats"][0]["event_type"] == "PRODUCT_VIEW"
