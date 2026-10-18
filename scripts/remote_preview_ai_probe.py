"""Private tagged-revision BGE/Claude checks; credentials only arrive on stdin.

Uses the existing fixed acceptance database and least-privilege role guards.
Creates only marker-owned fixtures and removes them even when HTTP checks fail.
"""
import json
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from time import perf_counter

from bs4 import BeautifulSoup
from bson import Decimal128, ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from remote_d4_consumer_probe import (
    DATABASE, cleanup_probe, login, make_event, monitor_count, page,
    recommendations, require, verify_database_roles, verify_scope,
)

INTENTS = ("period_compare", "replenishment", "promotion", "revenue_change")


def validate(config):
    verify_scope(config)
    require(type(config.get("expect_claude", False)) is bool, "Claude expectation must be boolean")


def admin_denied(response):
    require(response.status_code == 403 or (response.status_code in (302, 303)
            and response.headers.get("Location") == "/"), "Customer reached AI admin")


def measured_page(session, url):
    started = perf_counter()
    response = session.get(url, timeout=190)
    require(response.status_code == 200, f"AI page HTTP {response.status_code}")
    return BeautifulSoup(response.text, "html.parser"), round((perf_counter() - started) * 1000)


def cache_counts(soup):
    require(not soup.select_one(".model-warning"), "Real BGE model unavailable")
    require(soup.select_one(".similar-row .score-value"), "Real similarity scores missing")
    text = soup.get_text(" ", strip=True)
    match = re.search(r"快取命中\s*(\d+)\s*/\s*(\d+)", text)
    require(match is not None, "BGE cache measurement missing")
    scores = [float(node.get_text(strip=True)) for node in soup.select(".score-value")]
    require(all(-1 <= score <= 1 for score in scores), "Invalid BGE similarity score")
    return {"hits": int(match[1]), "total": int(match[2]), "scores": scores}


def run(config):
    validate(config)
    client = MongoClient(config["mongo_uri"], serverSelectionTimeoutMS=15000)
    db = client[DATABASE]
    verify_database_roles(client)
    marker = "sam-ai-" + secrets.token_hex(8)
    user_ids = [ObjectId() for _ in range(3)]
    product_ids, sku_ids = [ObjectId() for _ in range(2)], [ObjectId() for _ in range(2)]
    password = secrets.token_urlsafe(24)
    base = config["service_url"].rstrip("/")
    report = {"status": "failed", "probe_id": marker,
              "revision": config["revision"], "image": config["image"],
              "expect_claude": config.get("expect_claude", False)}
    try:
        fixture = db.products.find_one({"schema_version": 4, "status": "active"})
        require(fixture and len(fixture.get("category_path", [])) >= 2, "Acceptance fixture missing")
        now = datetime.now(timezone.utc)
        names = ("隔離驗收瑜珈墊伸展運動", "隔離驗收高蛋白營養飲品")
        db.products.insert_many([{"_id": product_ids[i], "schema_version": 4,
            "product_code": f"{marker}-{i}", "product_name": name,
            "major_category_id": fixture["major_category_id"],
            "minor_category_id": fixture["minor_category_id"],
            "category_path": fixture["category_path"], "average_rating_display": 0,
            "image_urls": [], "summary": name, "status": "active",
            "is_ai_recommendable": True, "acceptance_run": marker, "created_at": now}
            for i, name in enumerate(names)])
        db.product_skus.insert_many([{"_id": sku_ids[i], "schema_version": 4,
            "product_id": product_ids[i], "sku_code": f"{marker}-sku-{i}",
            "variant_attributes": {}, "status": "active", "price": Decimal128("10.00"),
            "available_quantity": 10, "stock_quantity": 10, "reserved_quantity": 0,
            "safety_stock": 0, "acceptance_run": marker, "created_at": now} for i in range(2)])
        roles = ("admin", "customer", "customer")
        emails = [f"{marker}-{i}@example.invalid" for i in range(3)]
        db.users.insert_many([{"_id": uid, "schema_version": 4, "status": "active",
            "is_active": True, "role": roles[i], "email": emails[i], "display_name": "AI隔離驗收",
            "password_hash": generate_password_hash(password), "acceptance_run": marker,
            "created_at": now, "updated_at": now} for i, uid in enumerate(user_ids)])
        report["stage"] = "login"
        admin, member, other = [login(base, config["id_token"], email, password) for email in emails]
        report["stage"] = "role_rejection"
        denied = member.get(base + "/admin/ai/recommendation", timeout=30, allow_redirects=False)
        admin_denied(denied)
        report["customer_ai_admin_http"] = denied.status_code
        report["stage"] = "bge"
        url = base + "/admin/ai/recommendation?product_id=" + str(product_ids[0])
        first, elapsed = measured_page(admin, url)
        second, cached_elapsed = measured_page(admin, url)
        first_cache, second_cache = cache_counts(first), cache_counts(second)
        require(second_cache["total"] > 0 and second_cache["hits"] == second_cache["total"],
                "Second BGE request did not use cached vectors")
        report["bge"] = {"first_http_ms": elapsed, "cached_http_ms": cached_elapsed,
                         "first": first_cache, "second": second_cache,
                         "real_scores": True, "first_request_is_not_claimed_cold_start": True}
        report["stage"] = "personalization"
        monitor_url = base + "/admin/recommendations"
        count = monitor_count(page(admin, monitor_url))
        other_before = recommendations(page(other, base + "/"))
        demo = make_event(user_ids[1], product_ids[0], marker, now, False)
        demo["event_type"] = "PURCHASE"
        demo["metadata"].update(demo_checkout=True, exclude_from_attribution=True)
        db.behavior_events.insert_one(demo)
        own_cards = recommendations(page(member, base + "/"))
        require(own_cards and str(product_ids[0]) in own_cards[0][0], "Demo purchase did not seed own ranking")
        require(monitor_count(page(admin, monitor_url)) == count, "Demo purchase leaked into attribution")
        require(recommendations(page(other, base + "/")) == other_before, "Another member learned from demo purchase")
        db.behavior_events.insert_many([make_event(user_ids[1], product_ids[1], marker,
            now + timedelta(seconds=i + 1), True) for i in range(60)])
        require(recommendations(page(member, base + "/")) == own_cards, "Synthetic history changed own ranking")
        require(monitor_count(page(admin, monitor_url)) == count, "Synthetic history changed monitoring")
        report["personalization"] = {"demo_purchase_in_own_ranking": True,
            "other_member_unchanged": True, "demo_and_synthetic_excluded_from_monitor": True,
            "synthetic_excluded_before_limit": True}
        report["stage"] = "insight_form"
        insight = page(admin, base + "/admin/ai/insight")
        form = insight.find("form", method="post")
        require(form is not None, "Insight form unavailable")
        data = {node["name"]: node.get("value", "") for node in form.select("input[name]")}
        require(data.get("csrf_token"), "CSRF missing")
        report["intents"] = []
        for intent in INTENTS:
            report["stage"] = intent
            started = perf_counter()
            response = admin.post(base + "/admin/ai/insight", data={**data, "intent": intent}, timeout=90)
            require(response.status_code == 200, "Fixed insight intent unavailable")
            result = BeautifulSoup(response.text, "html.parser").select_one("#answer")
            require(result is not None, "Insight answer missing")
            is_claude = result.select_one(".source-badge.cloud") is not None
            badge = result.select_one(".source-badge")
            report["last_intent"] = {"intent": intent, "source": "claude" if is_claude else "rules",
                "label": badge.get_text(" ", strip=True) if badge else None}
            require(is_claude is config.get("expect_claude", False), "Claude result differs from configured expectation")
            require("請人工核對" in result.get_text(), "AI review label missing")
            request_node = BeautifulSoup(response.text, "html.parser").select_one(".payload-preview code")
            require(request_node is not None, "Actual model payload preview missing")
            sent = json.loads(request_node.get_text())
            payload = sent["data"]
            require(set(payload) == {"contract_version", "timezone", "currency", "generated_at", "source",
                "current_range", "comparison_range", "totals", "daily", "products", "products_meta", "unavailable", "warnings"}
                and payload["contract_version"] == "ai-whitelist-v1", "Payload whitelist mismatch")
            require(all(set(product) == {"product_id", "name", "sku_id", "price", "stock_quantity",
                "available_quantity", "safety_stock", "valid_sold_units", "promotion_eligible"}
                for product in payload["products"]), "Product payload whitelist mismatch")
            require(not any(value in request_node.get_text() for value in (*emails, password, "password_hash", "user_id")),
                    "Member data in model payload")
            usage = re.search(r"輸入\s*(\d+)／輸出\s*(\d+)\s*tokens", result.get_text(" ", strip=True))
            if is_claude:
                require(usage and int(usage[1]) > 0 and int(usage[2]) > 0, "Claude usage missing")
                require(result.select_one(".ai-text") and len(result.select_one(".ai-text").get_text()) > 30,
                        "Claude answer empty")
                require(not result.select_one(".field-error"), "Claude answer truncated")
            report["intents"].append({"intent": intent, "http": response.status_code,
                "source": "claude" if is_claude else "rules", "http_ms": round((perf_counter() - started) * 1000),
                "input_tokens": int(usage[1]) if usage else None,
                "output_tokens": int(usage[2]) if usage else None,
                "answer_text": result.select_one(".ai-text").get_text(" ", strip=True),
                "input_totals": payload["totals"], "input_products": [{key: product[key]
                    for key in ("name", "price", "available_quantity", "safety_stock", "valid_sold_units")}
                    for product in payload["products"]], "input_warnings": payload["warnings"],
                "whitelist_and_member_data_check": True})
            if intent == INTENTS[0] and is_claude:
                repeated = admin.post(base + "/admin/ai/insight", data={**data, "intent": intent}, timeout=90)
                cached = BeautifulSoup(repeated.text, "html.parser").select_one("#answer")
                require(repeated.status_code == 200 and cached and "快取結果" in cached.get_text(),
                        "Claude identical request was not cached")
                require(cached.select_one(".ai-text").get_text() == result.select_one(".ai-text").get_text(),
                        "Claude cache changed answer")
                report["claude_cache_repeated_request"] = True
        blocked = admin.post(base + "/admin/ai/insight", data={**data, "intent": "free_question", "question": "test"}, timeout=30)
        require(blocked.status_code == 403, "Free questions unexpectedly enabled")
        compare = page(admin, base + "/admin/ai/compare")
        require("相似商品" in compare.get_text(), "BGE comparison measurement missing")
        report.update(status="passed", free_question_http=403,
                      comparison_page_http=200, real_claude_calls_expected=4 if config.get("expect_claude") else 0)
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error) if isinstance(error, RuntimeError) else "Probe failed")
    finally:
        report["cleanup"] = cleanup_probe(db, marker, user_ids, sku_ids, product_ids)
        if not report["cleanup"]["verified"]:
            report["status"] = "cleanup_failed"
        client.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1)
