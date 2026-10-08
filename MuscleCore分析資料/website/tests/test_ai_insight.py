"""Cloud insight (AI panel B): whitelist v1 payload, intents, guards and fallbacks (T2 / R09)."""
import json
from decimal import Decimal
import pytest
from bson import Decimal128, ObjectId
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from test_v4_routes import shop
from test_dashboard import order
from app.services.ai_payload import InsightDataError, build_insight_payload, insight_ranges
from app.services.ai_workflows import InsightRequestError, clean_question

PAYLOAD_KEYS = {"contract_version", "timezone", "currency", "generated_at", "source", "current_range", "comparison_range",
                "totals", "daily", "products", "products_meta", "unavailable", "warnings"}
PRODUCT_KEYS = {"product_id", "name", "sku_id", "price", "stock_quantity", "available_quantity", "safety_stock",
                "valid_sold_units", "promotion_eligible"}


@pytest.fixture
def admin(shop):
    app, client, db, uid, pid, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    return app, client, db, uid, pid, sid


def fake_claude(app, reply="本期營收如資料所示。", calls=None):
    calls = [] if calls is None else calls
    def respond(prompt):
        calls.append(prompt.to_string())
        return AIMessage(content=reply, usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150})
    app.config.update(AI_SUMMARY_ENABLED=True, CLAUDE_MODEL="test-model", CLAUDE_FACTORY=lambda: RunnableLambda(respond))
    return calls


def ask(client, intent, question="", start="2026-10-01", end="2026-10-07", demo="all", csrf="test-csrf"):
    return client.post("/admin/ai/insight", data={"csrf_token": csrf, "intent": intent, "question": question,
                                                  "start": start, "end": end, "demo": demo})


def payload_for(db, start, end, demo="all", intent=None):
    current, comparison = insight_ranges(db, {"start": start, "end": end, "demo": demo})
    return build_insight_payload(db, "v4", current, comparison, intent)


def test_payload_whitelist_totals_daily_and_comparison(admin):
    _, _, db, _, pid, _ = admin
    valid = order(db, "c1", "2026-10-02T02:00:00+00:00", "100.00")
    order(db, "c2", "2026-10-03T02:00:00+00:00", "999.00", payment_status="unpaid")
    order(db, "p1", "2026-09-27T02:00:00+00:00", "50.00")
    db.order_items.insert_one({"order_id": valid, "product_id": pid, "product_name_snapshot": "啞鈴", "quantity": 3})
    db.users.update_many({}, {"$set": {"email": "private@example.test", "birthday": "2000-01-01"}})
    payload = payload_for(db, "2026-10-01", "2026-10-07")
    assert set(payload) == PAYLOAD_KEYS and set(payload["products"][0]) == PRODUCT_KEYS
    assert payload["comparison_range"] == {"start": "2026-09-24", "end": "2026-09-30", "days": 7}
    assert payload["totals"]["current"] == {"all_orders": 2, "valid_orders": 1, "revenue": "100.00", "average_order_value": "100.00"}
    assert payload["totals"]["change_pct"]["revenue"] == "100.0"
    assert len(payload["daily"]["current"]) == 7 and payload["daily"]["current"][0]["all_orders"] == 0
    assert payload["products"][0]["valid_sold_units"] == 3 and payload["products"][0]["promotion_eligible"] is None
    text = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("private@example.test", "password_hash", "2000-01-01", "測試會員", "email"):
        assert forbidden not in text


def test_zero_data_and_zero_base_give_null_growth(admin):
    _, _, db, _, _, _ = admin
    payload = payload_for(db, "2026-10-01", "2026-10-07")
    totals = payload["totals"]
    assert totals["current"]["average_order_value"] is None and totals["current"]["revenue"] == "0.00"
    assert all(value is None for value in totals["change_pct"].values())
    assert "本期沒有任何訂單。" in payload["warnings"]


def test_demo_exclusion_applies_to_both_periods(admin):
    _, _, db, _, _, _ = admin
    order(db, "real", "2026-10-02T02:00:00+00:00", "10.00")
    order(db, "demo", "2026-10-02T02:00:00+00:00", "90.00", is_demo=True)
    order(db, "demo-old", "2026-09-28T02:00:00+00:00", "90.00", is_demo=True)
    excluded = payload_for(db, "2026-10-01", "2026-10-07", demo="exclude")
    assert excluded["totals"]["current"]["revenue"] == "10.00" and excluded["totals"]["comparison"]["all_orders"] == 0
    assert excluded["source"]["demo_orders"] == {"current": 0, "comparison": 0}
    included = payload_for(db, "2026-10-01", "2026-10-07")
    assert included["source"]["demo_orders"] == {"current": 1, "comparison": 1}
    assert any("示範訂單" in w for w in included["warnings"])


def test_366_days_allowed_367_rejected(admin):
    _, _, db, _, _, _ = admin
    payload = payload_for(db, "2024-01-01", "2024-12-31")  # leap year: 366 days
    assert payload["current_range"]["days"] == 366 and len(payload["daily"]["comparison"]) == 366
    with pytest.raises(InsightDataError) as error:
        insight_ranges(db, {"start": "2024-01-01", "end": "2025-01-01"})
    assert error.value.code == "invalid_range"


def test_order_cap_rejects_instead_of_truncating(admin, monkeypatch):
    _, client, db, _, _, _ = admin
    monkeypatch.setattr("app.services.ai_payload.MAX_PERIOD_ORDERS", 2)
    for name in ("a", "b"):
        order(db, name, "2026-10-02T02:00:00+00:00")
    assert payload_for(db, "2026-10-01", "2026-10-07")["totals"]["current"]["all_orders"] == 2
    order(db, "c", "2026-10-02T02:00:00+00:00")
    with pytest.raises(InsightDataError) as error:
        payload_for(db, "2026-10-01", "2026-10-07")
    assert error.value.code == "range_too_large"
    response = client.get("/admin/ai/insight?start=2026-10-01&end=2026-10-07")
    assert response.status_code == 400 and "超過 2 筆訂單" in response.get_data(as_text=True)


def test_candidates_only_sellable_and_lowest_sellable_price(admin):
    _, _, db, _, pid, sid = admin
    db.product_skus.insert_many([
        {"product_id": pid, "sku_code": "CHEAP-OFF", "status": "inactive", "price": Decimal128("1.00"), "available_quantity": 5, "stock_quantity": 5, "safety_stock": 1},
        {"product_id": pid, "sku_code": "CHEAP-EMPTY", "status": "active", "price": Decimal128("2.00"), "available_quantity": 0, "stock_quantity": 0, "safety_stock": 1}])
    for status, recommendable in (("inactive", True), ("active", False)):
        other = db.products.insert_one({"product_name": f"{status}-{recommendable}", "status": status, "is_ai_recommendable": recommendable}).inserted_id
        db.product_skus.insert_one({"product_id": other, "status": "active", "price": Decimal128("5.00"), "available_quantity": 9, "stock_quantity": 9, "safety_stock": 1})
    no_stock = db.products.insert_one({"product_name": "缺貨", "status": "active", "is_ai_recommendable": True}).inserted_id
    db.product_skus.insert_one({"product_id": no_stock, "status": "active", "price": Decimal128("5.00"), "available_quantity": 0, "stock_quantity": 0, "safety_stock": 1})
    payload = payload_for(db, "2026-10-01", "2026-10-07")
    assert [p["product_id"] for p in payload["products"]] == [str(pid)]
    assert payload["products"][0]["price"] == "10.25" and payload["products"][0]["sku_id"] == str(sid)
    assert payload["products_meta"]["excluded_without_sellable_sku"] == 1


def test_products_sorted_per_intent_and_truncation_marked(admin, monkeypatch):
    _, _, db, _, pid, _ = admin
    monkeypatch.setattr("app.services.ai_payload.MAX_PRODUCTS", 1)
    low = db.products.insert_one({"product_name": "快缺貨", "status": "active", "is_ai_recommendable": True}).inserted_id
    db.product_skus.insert_one({"product_id": low, "status": "active", "price": Decimal128("5.00"), "available_quantity": 1, "stock_quantity": 1, "safety_stock": 4})
    payload = payload_for(db, "2026-10-01", "2026-10-07", intent="replenishment")
    assert payload["products"][0]["name"] == "快缺貨" and payload["products_meta"]["truncated"]
    assert payload["products_meta"]["sort"] == "available_minus_safety_asc" and any("只列前 1 筆" in w for w in payload["warnings"])


def test_default_range_ends_at_latest_order_date(admin):
    _, client, db, _, _, _ = admin
    order(db, "latest", "2026-08-15T20:00:00+00:00")  # 08-16 in Taipei
    html = client.get("/admin/ai/insight").get_data(as_text=True)
    assert 'value="2026-08-10"' in html and 'value="2026-08-16"' in html


def test_preset_intent_uses_fake_model_and_preview_is_the_sent_request(admin):
    app, client, db, _, _, _ = admin
    calls = fake_claude(app, reply='<script>alert("x")</script>')
    order(db, "c1", "2026-10-02T02:00:00+00:00", "100.00")
    response = ask(client, "period_compare", question="這段文字不應送出")
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and len(calls) == 1
    assert "&lt;script&gt;" in html and '<script>alert' not in html
    assert "test-model" in html and "輸入 120／輸出 30 tokens" in html and "請人工核對" in html and "本次實際傳送" in html
    assert "這段文字不應送出" not in calls[0]
    sent = json.loads(calls[0].split("以下 JSON 為本次請求：\n", 1)[1])
    assert sent["intent"] == "period_compare" and sent["untrusted_question"] is None
    assert sent["data"]["totals"]["current"]["revenue"] == "100.00"
    # The <details> preview shows the same serialized object that reached the model.
    preview = html.split("<pre><code>", 1)[1].split("</code></pre>", 1)[0]
    assert json.loads(preview.replace("&#34;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")) == sent


def test_free_question_isolated_as_untrusted_input(admin):
    app, client, _, _, _, _ = admin
    calls = fake_claude(app)
    assert ask(client, "free_question", question="本期哪一天營收最高？\x07").status_code == 200
    assert "不可信" in calls[0] and '"untrusted_question": "本期哪一天營收最高？"' in calls[0]


@pytest.mark.parametrize("question,code", [
    ("", "invalid_question"), ("問" * 301, "invalid_question"),
    ("寄到 boss@example.com", "pii_detected"), ("打 0912-345-678", "pii_detected"),
    ("A123456789 的訂單", "pii_detected"), ("(02)-2345678", "pii_detected")])
def test_free_question_guards_reject_before_sending(question, code):
    with pytest.raises(InsightRequestError) as error:
        clean_question(question)
    assert error.value.code == code


def test_guard_rejection_does_not_call_model(admin):
    app, client, _, _, _, _ = admin
    calls = fake_claude(app)
    response = ask(client, "free_question", question="客戶 boss@example.com 買了什麼")
    assert response.status_code == 422 and not calls and "未送出" in response.get_data(as_text=True)
    assert ask(client, "free_question", question="問" * 300).status_code == 200 and len(calls) == 1


def test_unknown_intent_and_csrf_rejected(admin):
    app, client, _, _, _, _ = admin
    calls = fake_claude(app)
    assert ask(client, "delete_everything").status_code == 400
    assert ask(client, "period_compare", csrf="wrong").status_code == 400
    assert not calls


def test_cache_reuses_same_request_and_separates_intents(admin):
    app, client, _, _, _, _ = admin
    calls = fake_claude(app)
    ask(client, "replenishment")
    second = ask(client, "replenishment").get_data(as_text=True)
    assert len(calls) == 1 and "快取" in second
    ask(client, "promotion")
    ask(client, "replenishment", demo="exclude")
    assert len(calls) == 3


def test_rate_limit_per_admin(admin):
    app, client, _, _, _, _ = admin
    calls = fake_claude(app)
    app.config["AI_INSIGHT_RATE_LIMIT"] = 2
    ask(client, "free_question", question="問題一")
    ask(client, "free_question", question="問題二")
    response = ask(client, "free_question", question="問題三")
    assert response.status_code == 429 and len(calls) == 2


def test_failure_falls_back_to_rules_without_exposing_error(admin):
    app, client, db, _, pid, sid = admin
    db.product_skus.update_one({"_id": sid}, {"$set": {"available_quantity": 1, "safety_stock": 3}})
    class ReadTimeout(Exception):
        pass
    def broken():
        def fail(prompt):
            raise ReadTimeout("secret-host.example")
        return RunnableLambda(fail)
    app.config.update(AI_SUMMARY_ENABLED=True, CLAUDE_MODEL="test-model", CLAUDE_FACTORY=broken)
    html = ask(client, "replenishment").get_data(as_text=True)
    assert "規則退回 · 逾時" in html and "secret-host" not in html
    assert "補貨候選：啞鈴（可售 1／安全庫存 3" in html and "已送出但呼叫失敗" in html


def test_disabled_or_unconfigured_is_labelled_not_sent(admin):
    app, client, _, _, _, _ = admin
    html = ask(client, "revenue_change").get_data(as_text=True)
    assert "規則退回 · 雲端 AI 未啟用" in html and "未送出" in html and "無法判定原因" in html
    app.config.update(AI_SUMMARY_ENABLED=True, ANTHROPIC_API_KEY="", CLAUDE_MODEL="")
    app.config.pop("CLAUDE_FACTORY", None)
    html = ask(client, "period_compare").get_data(as_text=True)
    assert "未設定 API Key 或模型" in html and "未送出" in html


def test_calls_are_measured_without_question_text(admin):
    app, client, _, _, _, _ = admin
    fake_claude(app)
    ask(client, "free_question", question="秘密問題內容")
    log = list(app.extensions["ai_calls"])
    assert log[-1]["intent"] == "free_question" and log[-1]["input_tokens"] == 120
    assert "秘密問題內容" not in json.dumps(log, ensure_ascii=False)


def test_overview_summary_shares_measured_claude_call(admin):
    app, client, _, _, _, _ = admin
    fake_claude(app, reply="總覽摘要")
    client.post("/admin/summary", headers={"X-CSRF-Token": "test-csrf"})
    assert app.extensions["ai_calls"][-1]["kind"] == "summary"


def test_insight_page_requires_admin(shop):
    _, client, _, _, _, _ = shop
    assert client.get("/admin/ai/insight").status_code == 302
    assert ask(client, "period_compare").status_code == 302


def test_nav_links_insight_page(admin):
    _, client, _, _, _, _ = admin
    html = client.get("/admin/").get_data(as_text=True)
    assert 'href="/admin/ai/insight"' in html
