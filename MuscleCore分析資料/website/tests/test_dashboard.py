from datetime import datetime, timezone
from decimal import Decimal
import pytest
from bson import Decimal128
from flask import g
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage
from test_v4_routes import shop, post
from app.services.dashboard import dashboard_filters, load_dashboard, DashboardFilterError, recommendation_monitor


def order(db, number, at, amount="10.25", **extra):
    document = {"order_number": number, "ordered_at": datetime.fromisoformat(at),
                "created_at": datetime.fromisoformat(at), "payment_status": "paid", "status": "confirmed",
                "is_demo": False, "total_amount": Decimal128(amount), **extra}
    return db.orders.insert_one(document).inserted_id


def test_taipei_boundaries_and_payment_filters(shop):
    _, _, db, _, pid, _ = shop
    order(db, "before", "2026-09-30T15:59:59+00:00")
    inside = order(db, "inside", "2026-09-30T16:00:00+00:00", "10.25")
    order(db, "last", "2026-10-01T15:59:59+00:00", "20.50")
    order(db, "after", "2026-10-01T16:00:00+00:00")
    order(db, "unpaid", "2026-10-01T00:00:00+00:00", payment_status="unpaid")
    order(db, "refund", "2026-10-01T00:00:00+00:00", payment_status="refunded")
    order(db, "cancel", "2026-10-01T00:00:00+00:00", status="cancelled")
    db.order_items.insert_one({"order_id": inside, "product_id": pid, "product_name_snapshot": "測試商品", "quantity": 2})
    data, _ = load_dashboard(db, "v4", dashboard_filters({"start": "2026-10-01", "end": "2026-10-01"}))
    assert data["revenue"] == Decimal("30.75") and data["orders"] == 2
    assert data["sampled_orders"] == 5 and data["best"][0]["sales_count"] == 2
    assert data["daily"] == [{"date": "2026-10-01", "orders": 2, "revenue": Decimal("30.75")}]


@pytest.mark.parametrize("values", [{"start": "2026-10-01"}, {"start": "bad", "end": "bad"},
    {"start": "2026-10-02", "end": "2026-10-01"}, {"start": "2020-01-01", "end": "2026-01-01"}, {"demo": "unknown"}])
def test_invalid_filter_is_explicit(values):
    with pytest.raises(DashboardFilterError):
        dashboard_filters(values)


def test_demo_filter_stock_scope_and_decimal_rendering(shop):
    _, client, db, uid, _, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    db.product_skus.update_one({"_id": sid}, {"$set": {"available_quantity": 1}})
    order(db, "real", "2026-10-01T00:00:00+00:00", "123.45")
    order(db, "demo", "2026-10-01T00:00:00+00:00", "999.99", is_demo=True)
    data, _ = load_dashboard(db, "v4", dashboard_filters({"demo": "exclude"}))
    assert data["orders"] == 1 and data["revenue"] == Decimal("123.45")
    assert data["low_stock_count"] == 1
    page = client.get("/admin/?demo=exclude").get_data(as_text=True)
    assert "123.45" in page and "TEST-1" in page and "999.99" not in page
    assert client.get("/admin/?start=bad&end=bad").status_code == 400


def test_explicit_range_does_not_silently_truncate(shop, monkeypatch):
    _, _, db, _, _, _ = shop
    monkeypatch.setattr("app.services.dashboard.MAX_RANGE_ORDERS", 1)
    for name in ("a", "b"):
        order(db, name, "2026-10-01T00:00:00+00:00")
    with pytest.raises(DashboardFilterError):
        load_dashboard(db, "v4", dashboard_filters({"start": "2026-10-01", "end": "2026-10-01"}))


def test_summary_scope_cache_csrf_and_html_escape(shop):
    app, client, db, uid, _, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    calls = []
    def respond(prompt):
        calls.append(prompt.to_string())
        return AIMessage(content='<script>alert("x")</script>')
    app.config.update(AI_SUMMARY_ENABLED=True, CLAUDE_FACTORY=lambda: RunnableLambda(respond))
    url = "/admin/summary?start=2026-10-01&end=2026-10-01&demo=exclude"
    assert client.post(url).status_code == 400
    assert client.get("/admin/").status_code == 200 and not calls
    page = post(client, url)
    assert page.status_code == 200 and b"&lt;script&gt;" in page.data and b"<script>" not in page.data
    post(client, url)
    assert len(calls) == 1 and '"scope": "date_range"' in calls[0] and '"demo": "exclude"' in calls[0]
    post(client, url.replace("exclude", "only"))
    assert len(calls) == 2
    db.users.update_one({"_id": uid}, {"$set": {"role": "customer"}})
    assert post(client, url).status_code == 302 and len(calls) == 2


def test_monitor_uses_v4_event_names_and_stored_policy(shop):
    _, client, db, uid, pid, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    db.behavior_events.insert_many([{"product_id": pid, "event_type": "ADD_TO_CART", "event_at": datetime.now(timezone.utc)} for _ in range(2)])
    db.system_configs.insert_one({"config_key": "recommendation_policy", "status": "active", "settings": {"weights": {"ADD_TO_CART": 3}}})
    result = recommendation_monitor(db, "v4")
    assert result["stats"][0]["count"] == 2 and result["policy"]["weights"]["ADD_TO_CART"] == 3
    page = client.get("/admin/recommendations")
    assert page.status_code == 200 and b"ADD_TO_CART" in page.data
