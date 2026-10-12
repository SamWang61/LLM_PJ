"""Admin shared layout, overview KPI wording and monitor policy (T1 / R05)."""
import re
from datetime import datetime
import pytest
from bson import Decimal128, ObjectId
from test_v4_routes import shop
from test_dashboard import order
from app.services.ai_workflows import summary_metrics


@pytest.fixture
def admin(shop):
    app, client, db, uid, pid, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    with client.session_transaction() as state:
        state.update(role="admin", name="測試管理員")
    return app, client, db, uid, pid, sid


def page(client, url):
    response = client.get(url)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_layout_navigation_header_and_status(admin):
    _, client, _, _, _, _ = admin
    html = page(client, "/admin/")
    assert 'aria-label="後台導覽"' in html and "css/admin.css" in html
    assert re.search(r'href="/admin/"\s+aria-current="page"', html)
    assert 'href="/admin/recommendations"' in html and "尚未開放" in html  # unbuilt pages are disabled, not 404 links
    assert "管理員：測試管理員" in html and "回商城" in html and "/auth/logout" in html
    assert "購物車" not in html  # admin header is separate from the storefront header
    assert "資料庫" in html and "BGE" in html and "雲端 LLM" in html and "未啟用" in html
    assert "讀取時間" in html and "模式 v4" in html


def test_status_light_never_claims_unconfigured_llm(admin):
    app, client, _, _, _, _ = admin
    app.config.update(AI_SUMMARY_ENABLED=True, ANTHROPIC_API_KEY="", CLAUDE_MODEL="")
    assert "未設定，退回規則" in page(client, "/admin/")


def test_kpi_uses_valid_over_all_orders_and_null_average(admin):
    _, client, db, _, _, _ = admin
    order(db, "unpaid", "2026-10-01T00:00:00+00:00", payment_status="unpaid")
    order(db, "cancel", "2026-10-01T00:00:00+00:00", status="cancelled")
    html = page(client, "/admin/?start=2026-10-01&end=2026-10-01")
    assert "有效／全部訂單" in html and "<strong>0 / 2</strong>" in html
    assert "無有效訂單，不計算" in html and "<strong>—</strong>" in html
    assert "此範圍尚無有日期的有效訂單" in html and "尚無符合條件的銷售明細" in html


def test_summary_payload_sends_null_average_instead_of_zero():
    metrics = summary_metrics({"revenue": 0, "orders": 0, "avg_order": None, "low_stock": []})
    assert metrics["average_order_value"] is None


def test_filters_apply_to_every_block(admin):
    _, client, db, _, pid, _ = admin
    real = order(db, "REAL-1", "2026-10-01T00:00:00+00:00", "100.00")
    demo = order(db, "DEMO-1", "2026-10-02T00:00:00+00:00", "50.00", is_demo=True)
    db.order_items.insert_many([
        {"order_id": real, "product_id": pid, "product_name_snapshot": "真實商品", "quantity": 1},
        {"order_id": demo, "product_id": ObjectId(), "product_name_snapshot": "示範商品", "quantity": 9}])
    everything = page(client, "/admin/?start=2026-10-01&end=2026-10-02")
    assert "DEMO-1" in everything and "示範商品" in everything and "示範資料 1 筆" in everything
    excluded = page(client, "/admin/?start=2026-10-01&end=2026-10-02&demo=exclude")
    for stale in ("DEMO-1", "示範商品", "2026-10-02</td>", "NT$ 50.00", "示範資料"):
        assert stale not in excluded
    assert "REAL-1" in excluded and "真實商品" in excluded and "<strong>1 / 1</strong>" in excluded
    assert "排除示範訂單" in excluded and "NT$ 100.00" in excluded


def test_daily_bar_chart_scales_to_peak(admin):
    _, client, db, _, _, _ = admin
    order(db, "a", "2026-10-01T00:00:00+00:00", "200.00")
    order(db, "b", "2026-10-02T00:00:00+00:00", "50.00")
    html = page(client, "/admin/?start=2026-10-01&end=2026-10-02")
    assert 'class="bar-chart"' in html and "height: 100.0%" in html and "height: 25.0%" in html


def test_filter_error_uses_admin_layout(admin):
    _, client, _, _, _, _ = admin
    response = client.get("/admin/?start=2026-10-02&end=2026-10-01")
    html = response.get_data(as_text=True)
    assert response.status_code == 400 and 'role="alert"' in html and 'aria-label="後台導覽"' in html


def test_flash_messages_render_as_timed_toasts(admin):
    _, client, _, _, _, _ = admin
    with client.session_transaction() as state:
        state["_flashes"] = [("success", "已儲存"), ("danger", "失敗了")]
    html = page(client, "/admin/")
    assert 'data-timeout="3500">已儲存' in html and 'data-timeout="6000">失敗了' in html


def test_monitor_reads_v4_policy_in_weight_order(admin):
    _, client, db, _, _, _ = admin
    db.system_configs.insert_one({"config_key": "recommendation_policy", "status": "active", "settings": {
        "weights": {"PRODUCT_VIEW": 1, "PURCHASE": 4, "SEARCH": 2, "ADD_TO_CART": 3}}})
    html = page(client, "/admin/recommendations")
    order_seen = [html.index(f"<code>{code}</code>") for code in ("PURCHASE", "ADD_TO_CART", "SEARCH", "PRODUCT_VIEW")]
    assert order_seen == sorted(order_seen) and "購買" in html
    assert "瀏覽 1、收藏 3" not in html and "尚無行為事件" in html
    assert re.search(r'href="/admin/recommendations"\s+aria-current="page"', html)


def test_monitor_without_policy_shows_empty_state(admin):
    _, client, _, _, _, _ = admin
    assert "尚未讀到有效的推薦政策" in page(client, "/admin/recommendations")


def test_customer_cannot_open_admin_layout(shop):
    _, client, _, _, _, _ = shop
    assert client.get("/admin/").status_code == 302
    assert client.get("/admin/recommendations").status_code == 302
