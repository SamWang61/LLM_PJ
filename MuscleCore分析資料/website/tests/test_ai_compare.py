"""AI comparison page (T4 / R09): only measured values, never sample numbers."""
import re
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from test_v4_routes import shop
from test_local_ai import KeywordEmbeddings
from app.admin import duration


@pytest.fixture
def admin(shop):
    app, client, db, uid, pid, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    return app, client, db, pid


def calls(app, *entries):
    with app.app_context():
        from app.services.ai_workflows import record_ai_call
        for entry in entries:
            record_ai_call(entry)


def page(client):
    response = client.get("/admin/ai/compare")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_unmeasured_shows_prompt_not_numbers(admin):
    _, client, _, _ = admin
    html = page(client)
    assert html.count("尚未量測") == 3 and 'href="/admin/ai/recommendation"' in html and 'href="/admin/ai/insight"' in html
    assert "本次啟動後尚無 AI 呼叫紀錄" in html and " ms" not in html.split("最近呼叫紀錄")[0]
    assert "網站讀 Atlas 與遠端商品圖片仍需網路" in html


def test_median_of_recent_ten_per_side(admin):
    app, client, _, _ = admin
    calls(app, *({"provider": "bge", "kind": "similar_products", "model": "bge", "latency_ms": ms} for ms in [9999] + [100] * 5 + [300] * 5))
    calls(app, {"provider": "bge", "kind": "refresh_vectors", "model": "bge", "latency_ms": 99999},
          {"provider": "claude", "kind": "insight", "model": "m", "latency_ms": 2000, "input_tokens": 1000, "output_tokens": 100},
          {"provider": "claude", "kind": "summary", "model": "m", "latency_ms": 4000, "input_tokens": 500, "output_tokens": 300})
    html = page(client)
    table = html.split("最近呼叫紀錄")[0]
    assert "<strong>200 ms</strong><small>最近 10 次中位數" in table  # oldest 9999 dropped; refresh not counted
    assert "<strong>3.0 秒</strong><small>最近 2 次中位數" in table
    assert "平均輸入 750／輸出 200 tokens" in table and "未設定 token 單價" in table


def test_cost_estimate_only_with_configured_prices(admin):
    app, client, _, _ = admin
    app.config.update(CLAUDE_INPUT_USD_PER_MTOK="3", CLAUDE_OUTPUT_USD_PER_MTOK="15")
    calls(app, {"provider": "claude", "kind": "insight", "model": "m", "latency_ms": 900, "input_tokens": 1000, "output_tokens": 100})
    assert "US$ 0.00450" in page(client)
    app.config.update(CLAUDE_OUTPUT_USD_PER_MTOK="not-a-number")
    assert "未設定 token 單價" in page(client)


def test_recent_calls_table_has_no_question_text(admin):
    app, client, _, _ = admin
    def respond(prompt):
        return AIMessage(content="回覆", usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
    app.config.update(AI_SUMMARY_ENABLED=True, CLAUDE_MODEL="test-model", CLAUDE_FACTORY=lambda: RunnableLambda(respond))
    client.post("/admin/ai/insight", data={"csrf_token": "test-csrf", "intent": "free_question", "question": "機密的問題文字",
                                           "start": "2026-10-01", "end": "2026-10-07", "demo": "all"})
    html = page(client)
    assert "機密的問題文字" not in html and "<code>free_question</code>" in html and "10／5" in html


def test_end_to_end_local_measurement_appears(admin):
    app, client, _, pid = admin
    app.config["EMBEDDINGS_FACTORY"] = KeywordEmbeddings
    client.get(f"/admin/ai/recommendation?product_id={pid}")
    html = page(client)
    assert re.search(r"<strong>\d+ ms</strong><small>最近 1 次中位數", html) and "相似商品" in html and "0/1" in html


@pytest.mark.parametrize("ms,text", [(None, "—"), (0, "0 ms"), (999, "999 ms"), (1000, "1.0 秒"), (12345, "12.3 秒")])
def test_duration_format(ms, text):
    assert duration(ms) == text


def test_compare_requires_admin(shop):
    _, client, _, _, _, _ = shop
    assert client.get("/admin/ai/compare").status_code == 302
