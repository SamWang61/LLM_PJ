"""Disposable private acceptance transaction check; JSON config arrives only on stdin."""

import json
import secrets
import sys
from datetime import datetime, timezone

import requests
from bson import Decimal128, ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from remote_d4_consumer_probe import login, page, require, verify_database_roles, verify_scope
from remote_member_transaction_checks import run as run_deep_checks
from remote_h05_h07_checks import cart_checks, event_checks


def cleanup_transaction_probe(db, marker, user_ids, sku_ids, product_id):
    """Delete and read back all fixture rows, including orphan SKU items."""
    require(db.name == "vibecart_acceptance_pr21", "Cleanup database scope mismatch")
    require(marker.startswith("ren-txn-") and user_ids and sku_ids,
            "Cleanup fixture scope missing")
    users_query = {"user_id": {"$in": user_ids}}
    order_ids = [row["_id"] for row in db.orders.find(users_query, {"_id": 1})]
    cart_ids = [row["_id"] for row in db.carts.find(users_query, {"_id": 1})]
    item_query = {"$or": [
        {"order_id": {"$in": order_ids}},
        {"sku_id": {"$in": sku_ids}},
    ]}
    scopes = (
        ("order_items", db.order_items, item_query),
        ("orders", db.orders, users_query),
        ("cart_events", db.cart_events, {"cart_id": {"$in": cart_ids}}),
        ("carts", db.carts, users_query),
        ("behavior_events", db.behavior_events, users_query),
        ("auth_sessions", db.auth_sessions, users_query),
        ("users", db.users, {"_id": {"$in": user_ids}, "acceptance_run": marker}),
        ("product_skus", db.product_skus, {"_id": {"$in": sku_ids}, "acceptance_run": marker}),
        ("products", db.products, {"_id": product_id, "acceptance_run": marker}),
    )
    cleanup = {}
    for name, collection, query in scopes:
        try:
            cleanup[name] = collection.delete_many(query).deleted_count
            cleanup[name + "_remaining"] = collection.count_documents(query)
        except Exception:
            cleanup[name] = "failed"
            cleanup[name + "_remaining"] = "readback_failed"
    cleanup["verified"] = all(isinstance(cleanup[name], int)
                              and cleanup[name + "_remaining"] == 0
                              for name, _, _ in scopes)
    return cleanup


def run(config):
    verify_scope(config)
    client = MongoClient(config["mongo_uri"], serverSelectionTimeoutMS=15000)
    db = client["vibecart_acceptance_pr21"]
    db.command("ping")
    verify_database_roles(client)
    marker = "ren-txn-" + secrets.token_hex(8)
    user_id, product_id, sku_id = ObjectId(), ObjectId(), ObjectId()
    user_ids, sku_ids = [user_id], [sku_id]
    email = marker + "@example.invalid"
    password = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    report = {"probe_id": marker, "service_revision": config["revision"],
              "service_image": config["image"], "status": "failed"}
    try:
        fixture = db.products.find_one({"schema_version": 4, "status": "active"},
                                       {"major_category_id": 1, "minor_category_id": 1,
                                        "category_path": 1})
        require(fixture and len(fixture.get("category_path", [])) >= 2,
                "Acceptance categories unavailable")
        db.products.insert_one({"_id": product_id, "schema_version": 4,
            "product_code": marker, "product_name": "REN 隔離交易驗收商品",
            "major_category_id": fixture["major_category_id"],
            "minor_category_id": fixture["minor_category_id"],
            "category_path": fixture["category_path"], "average_rating_display": 0,
            "image_urls": [], "summary": "測後刪除", "status": "active",
            "is_ai_recommendable": False, "acceptance_run": marker, "created_at": now})
        db.product_skus.insert_one({"_id": sku_id, "schema_version": 4,
            "product_id": product_id, "sku_code": marker + "-sku",
            "variant_attributes": {}, "status": "active", "price": Decimal128("10.00"),
            "available_quantity": 2, "stock_quantity": 2, "reserved_quantity": 0,
            "safety_stock": 0, "acceptance_run": marker, "created_at": now})
        db.users.insert_one({"_id": user_id, "schema_version": 4,
            "status": "active", "is_active": True, "role": "customer",
            "email": email, "display_name": "REN transaction probe",
            "password_hash": generate_password_hash(password),
            "acceptance_run": marker, "created_at": now, "updated_at": now})

        base = config["service_url"].rstrip("/")
        first = login(base, config["id_token"], email, password)
        second = login(base, config["id_token"], email, password)
        page(first, base + "/cart")
        page(second, base + "/cart")
        csrf = page(first, base + "/").select_one('form[action="/auth/logout"] input[name="csrf_token"]')
        require(csrf and csrf.get("value"), "Cart CSRF missing")
        first.headers["X-CSRF-Token"] = csrf["value"]
        require(db.auth_sessions.count_documents({"user_id": user_id, "revoked_at": None}) == 2,
                "Independent active sessions missing")
        admin = first.get(base + "/admin/", allow_redirects=False, timeout=30)
        require(admin.status_code in (302, 403), "Customer reached admin")
        cart, report['h05'] = cart_checks(db, first, base, marker, user_id, product_id, sku_id)
        report["add_http"] = report['h05']['http_statuses'][0]
        payload = {"cart_id": str(cart["_id"]), "expected_revision": cart['revision'],
                   "checkout_id": marker + "-checkout"}
        checkout = first.post(base + "/checkout", json=payload, timeout=30)
        require(checkout.status_code == 200, "Checkout failed")
        order = db.orders.find_one({"user_id": user_id, "checkout_id": payload["checkout_id"]})
        require(order and order.get("is_demo") is True, "Demo order persistence missing")
        require(db.order_items.count_documents({"order_id": order["_id"]}) == 1,
                "Order item persistence missing")
        require(db.product_skus.find_one({"_id": sku_id})["available_quantity"] == 1,
                "Stock decrement missing")
        retry = first.post(base + "/checkout", json=payload, timeout=30)
        require(retry.status_code == 200, "Idempotent checkout retry failed")
        conflict = first.post(base + "/checkout", json={**payload, "expected_revision": cart['revision'] + 1}, timeout=30)
        require(conflict.status_code == 409, "Checkout conflict was not rejected")
        require(db.orders.count_documents({"user_id": user_id}) == 1
                and db.order_items.count_documents({"order_id": order["_id"]}) == 1
                and db.product_skus.find_one({"_id": sku_id})["available_quantity"] == 1,
                "Retry or conflict changed persisted state")
        report['h07_events'] = event_checks(db, user_id, product_id, cart['_id'], order['_id'], marker)
        logout_form = page(first, base + "/").select_one('form[action="/auth/logout"] input[name="csrf_token"]')
        require(logout_form and logout_form.get("value"), "Logout CSRF missing")
        logout = first.post(base + "/auth/logout", data={"csrf_token": logout_form["value"]},
                            allow_redirects=False, timeout=30)
        require(logout.status_code in (302, 303), "First-device logout failed")
        require(first.get(base + "/cart", allow_redirects=False, timeout=30).status_code == 302,
                "Logged-out device retained cart access")
        require(second.get(base + "/cart", timeout=30).status_code == 200,
                "Second device was evicted")
        report.update(status="passed", two_device_sessions=True, customer_admin_denied=True,
                      add_to_cart=True, checkout_persisted=True, retry_same_order=True,
                      conflict_409=True, stock_after_checkout=1, per_device_logout=True)
        run_deep_checks(db, config, marker, user_id, product_id, sku_id, email, password,
                        user_ids, sku_ids, report)
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__,
                      error=str(error) if isinstance(error, RuntimeError) else "Probe execution failed")
    finally:
        cleanup = cleanup_transaction_probe(db, marker, user_ids, sku_ids, product_id)
        report["cleanup"] = cleanup
        if not cleanup["verified"]:
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
