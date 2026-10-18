"""B1: rule recommendations use the v4 recommendation_policy weights (4/3/2/1)."""
from datetime import datetime, timezone
import mongomock
import pytest
from test_v4_routes import shop
from app.services.recommendation import DEFAULT_WEIGHTS, policy_weights, recommend_products


def products():
    return [{"_id": "whey", "name": "乳清蛋白", "category": "營養", "rating": 0},
            {"_id": "mat", "name": "瑜珈墊", "category": "瑜珈", "rating": 0},
            {"_id": "bell", "name": "啞鈴", "category": "重訓", "rating": 0}]


def scores(events, weights=None):
    return {item["product"]["_id"]: item["score"] for item in recommend_products(products(), events, weights=weights)}


def test_defaults_are_v4_policy():
    assert DEFAULT_WEIGHTS == {"PURCHASE": 4, "ADD_TO_CART": 3, "SEARCH": 2, "PRODUCT_VIEW": 1}


@pytest.mark.parametrize("event_type,weight", [("PURCHASE", 4), ("ADD_TO_CART", 3), ("PRODUCT_VIEW", 1)])
def test_v4_event_weights(event_type, weight):
    # Score = category weight x2 + product weight (ratings and sales are zero here).
    assert scores([{"product_id": "whey", "event_type": event_type}])["whey"] == weight * 3


def test_search_event_credits_matching_products():
    result = scores([{"event_type": "SEARCH", "search_query": "瑜珈", "product_id": None}])
    assert result["mat"] == 2 * 3 and result["whey"] == 0 and result["bell"] == 0


def test_blank_search_and_unknown_events_add_nothing():
    result = scores([{"event_type": "SEARCH", "search_query": "  "}, {"product_id": "whey", "event_type": "UNKNOWN"}])
    assert set(result.values()) == {0}


def test_legacy_event_names_map_to_v4_weights():
    assert scores([{"product_id": "whey", "event_type": "purchase"}])["whey"] == 4 * 3
    assert scores([{"product_id": "whey", "event_type": "view"}])["whey"] == 1 * 3
    assert scores([{"product_id": "whey", "event_type": "favorite"}])["whey"] == 3 * 3


def test_custom_weights_override_defaults():
    weights = {**DEFAULT_WEIGHTS, "PRODUCT_VIEW": 5}
    assert scores([{"product_id": "whey", "event_type": "PRODUCT_VIEW"}], weights)["whey"] == 5 * 3


def test_policy_weights_reads_active_policy_and_ignores_invalid_values():
    db = mongomock.MongoClient().w
    assert policy_weights(db) == DEFAULT_WEIGHTS
    db.system_configs.insert_one({"config_key": "recommendation_policy", "status": "inactive",
                                  "settings": {"weights": {"PURCHASE": 9}}})
    assert policy_weights(db)["PURCHASE"] == 4
    db.system_configs.insert_one({"config_key": "recommendation_policy", "status": "active", "settings": {"weights": {
        "PURCHASE": 6, "SEARCH": -1, "ADD_TO_CART": "3", "PRODUCT_VIEW": True, "FAVORITE": 9}}})
    assert policy_weights(db) == {"PURCHASE": 6, "ADD_TO_CART": 3, "SEARCH": 2, "PRODUCT_VIEW": 1}


def test_storefront_uses_stored_policy(shop, monkeypatch):
    _, client, db, uid, pid, _ = shop
    db.system_configs.insert_one({"config_key": "recommendation_policy", "status": "active",
                                  "settings": {"weights": {"PRODUCT_VIEW": 7}}})
    db.behavior_events.insert_one({"user_id": uid, "product_id": pid, "event_type": "PRODUCT_VIEW",
                                   "event_at": datetime.now(timezone.utc)})
    captured = {}
    import app.services.ai_workflows as workflows
    original = workflows.recommend_products
    def spy(products, events, limit=4, weights=None):
        captured["weights"] = weights
        return original(products, events, limit, weights)
    monkeypatch.setattr(workflows, "recommend_products", spy)
    assert client.get("/").status_code == 200
    assert captured["weights"]["PRODUCT_VIEW"] == 7 and captured["weights"]["PURCHASE"] == 4
