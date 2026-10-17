"""Synthetic histories must not crowd out real events or seed BGE queries."""
from datetime import datetime, timedelta, timezone
import mongomock
import pytest
from test_v4_routes import shop
from app.services.behavior_scope import production_behavior_query, production_events
from app.services.dashboard import recommendation_monitor
from app.services.recommendation import recommend_products
from app.services.ai_workflows import build_recommendation_graph
from app import create_app
from flask import g
from bson import ObjectId
from app.services.sku_gateway import CartService


@pytest.mark.parametrize("metadata", [{"synthetic": True},
    {"synthetic_batch_id": "other-batch"}, {"exclude_from_attribution": True}])
def test_each_marker_excluded_in_database_and_memory(metadata):
    db = mongomock.MongoClient().test
    rows = [{"event_type": "view"}, {"metadata": {}},
            {"metadata": {"synthetic": False, "synthetic_batch_id": ""}},
            {"metadata": metadata}]
    db.behavior_events.insert_many(rows)
    assert len(list(db.behavior_events.find(production_behavior_query()))) == 3
    assert len(list(production_events(rows))) == 3


def test_monitor_filters_before_limit(shop):
    _, _, db, _, pid, _ = shop
    now = datetime.now(timezone.utc)
    db.behavior_events.insert_one({"product_id": pid, "event_type": "PRODUCT_VIEW", "event_at": now})
    db.behavior_events.insert_many([{"product_id": pid, "event_type": "PURCHASE",
        "event_at": now + timedelta(seconds=1), "metadata": {"synthetic": True}} for _ in range(1001)])
    result = recommendation_monitor(db, "v4")
    assert result["event_count"] == 1
    assert result["stats"] == [{"product_id": str(pid), "event_type": "PRODUCT_VIEW", "count": 1}]


def test_storefront_filters_before_limit_and_preserves_owner(shop, monkeypatch):
    _, client, db, uid, pid, _ = shop
    now = datetime.now(timezone.utc)
    db.behavior_events.insert_one({"user_id": uid, "product_id": pid, "event_type": "PRODUCT_VIEW", "event_at": now})
    db.behavior_events.insert_many([{"user_id": uid, "product_id": pid, "event_type": "PURCHASE",
        "event_at": now + timedelta(seconds=1), "metadata": {"synthetic_batch_id": "batch"}} for _ in range(51)])
    db.behavior_events.insert_one({"user_id": "another-user", "event_type": "PURCHASE", "event_at": now})
    captured = []
    def recommendations(products, events, query):
        captured.extend(events)
        return {"items": [], "source": "rules"}
    monkeypatch.setattr("app.store_v4.storefront_recommendations", recommendations)
    assert client.get("/").status_code == 200
    assert len(captured) == 1 and captured[0]["event_type"] == "PRODUCT_VIEW"


def test_rule_scores_unchanged_by_synthetic_events():
    products = [{"_id": "a", "category": "a", "rating": 0},
                {"_id": "b", "category": "b", "rating": 0}]
    real = [{"product_id": "a", "event_type": "view"}]
    synthetic = [{"product_id": "b", "event_type": "purchase", "metadata": {"synthetic": True}}] * 20
    assert recommend_products(products, real + synthetic) == recommend_products(products, real)


def test_direct_graph_does_not_seed_embeddings_from_synthetic_history():
    def forbidden_embeddings():
        pytest.fail("Synthetic history reached BGE")
    result = build_recommendation_graph(forbidden_embeddings).invoke({
        "products": [{"_id": "a", "name": "a", "category": "a", "stock": 1}],
        "events": [{"product_id": "a", "event_type": "PURCHASE", "metadata": {"synthetic": True}}],
        "query": ""})
    assert result["source"] == "rules" and result["events"] == []


@pytest.mark.parametrize("batch,expected", [
    ("legacy-offline-batch", "legacy-offline-batch"),
    ("", "legacy-demo"),
])
def test_legacy_writes_keep_server_synthetic_batch_on_all_events(batch, expected):
    db = mongomock.MongoClient().legacy
    uid, pid = ObjectId(), ObjectId()
    db.users.insert_one({"_id": uid, "is_active": True, "role": "customer"})
    db.products.insert_one({"_id": pid, "name": "測試商品", "is_active": True,
                            "category": "測試", "price": 10, "stock": 2, "sales_count": 0})
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATA_MODE": "legacy",
                      "BEHAVIOR_SYNTHETIC_BATCH": batch})

    @app.before_request
    def inject_database():
        g.db = db

    client = app.test_client()
    with client.session_transaction() as state:
        state.update(user_id=str(uid), csrf_token="test-csrf")
    assert client.get(f"/product/{pid}").status_code == 200
    assert client.post(f"/cart/add/{pid}", data={"csrf_token": "test-csrf"}).status_code == 302
    assert client.post("/checkout", data={"csrf_token": "test-csrf"}).status_code == 302
    events = list(db.behavior_events.find())
    assert {event["event_type"] for event in events} == {"view", "cart", "purchase"}
    assert all(event["metadata"] == {"synthetic": True,
        "synthetic_batch_id": expected, "exclude_from_attribution": True}
        for event in events)
    assert list(production_events(events)) == []


def test_purchase_attribution_follows_order_demo_flag():
    db = mongomock.MongoClient().test
    service = CartService(db)
    uid, pid, cid, oid = (ObjectId() for _ in range(4))
    product = {"_id": pid, "major_category_id": ObjectId(),
               "minor_category_id": ObjectId()}
    now = datetime.now(timezone.utc)
    demo = service._behavior(uid, product, 1, "PURCHASE", "demo", now, cid, oid,
                             is_demo=True)
    formal = service._behavior(uid, product, 1, "PURCHASE", "formal", now, cid, oid,
                               is_demo=False)
    assert demo["metadata"] == {"demo_checkout": True, "exclude_from_attribution": True}
    assert formal["metadata"] == {}
    assert list(production_events([demo, formal])) == [formal]
