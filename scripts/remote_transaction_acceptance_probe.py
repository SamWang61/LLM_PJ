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


def run(config):
    verify_scope(config)
    client = MongoClient(config["mongo_uri"], serverSelectionTimeoutMS=15000)
    db = client["vibecart_acceptance_pr21"]
    db.command("ping")
    verify_database_roles(client)
    marker = "ren-txn-" + secrets.token_hex(8)
    user_id, product_id, sku_id = ObjectId(), ObjectId(), ObjectId()
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
        csrf = page(first, base + "/auth/logout").select_one('input[name="csrf_token"]')
        require(csrf and csrf.get("value"), "Cart CSRF missing")
        first.headers["X-CSRF-Token"] = csrf["value"]
        require(db.auth_sessions.count_documents({"user_id": user_id, "revoked_at": None}) == 2,
                "Independent active sessions missing")
        admin = first.get(base + "/admin/", allow_redirects=False, timeout=30)
        require(admin.status_code in (302, 403), "Customer reached admin")
        data = {"sku_id": str(sku_id), "quantity": 1,
                "operation_id": marker + "-add"}
        add = first.post(base + "/cart/add/" + str(product_id), json=data, timeout=30)
        report["add_http"] = add.status_code
        require(add.status_code == 200, "Add-to-cart failed")
        cart = db.carts.find_one({"user_id": user_id, "status": "active"})
        require(cart and cart.get("revision") == 1, "Cart revision readback mismatch")
        payload = {"cart_id": str(cart["_id"]), "expected_revision": 1,
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
        conflict = first.post(base + "/checkout", json={**payload, "expected_revision": 2}, timeout=30)
        require(conflict.status_code == 409, "Checkout conflict was not rejected")
        require(db.orders.count_documents({"user_id": user_id}) == 1
                and db.order_items.count_documents({"order_id": order["_id"]}) == 1
                and db.product_skus.find_one({"_id": sku_id})["available_quantity"] == 1,
                "Retry or conflict changed persisted state")
        logout_form = page(first, base + "/auth/logout").select_one('input[name="csrf_token"]')
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
    except Exception as error:
        report.update(error_type=type(error).__name__,
                      error=str(error) if isinstance(error, RuntimeError) else "Probe execution failed")
    finally:
        order_ids = [row["_id"] for row in db.orders.find({"user_id": user_id}, {"_id": 1})]
        cart_ids = [row["_id"] for row in db.carts.find({"user_id": user_id}, {"_id": 1})]
        scopes = (
            ("order_items", db.order_items, {"order_id": {"$in": order_ids}}),
            ("orders", db.orders, {"user_id": user_id}),
            ("cart_events", db.cart_events, {"cart_id": {"$in": cart_ids}}),
            ("carts", db.carts, {"user_id": user_id}),
            ("behavior_events", db.behavior_events, {"user_id": user_id}),
            ("auth_sessions", db.auth_sessions, {"user_id": user_id}),
            ("users", db.users, {"_id": user_id, "acceptance_run": marker}),
            ("product_skus", db.product_skus, {"_id": sku_id, "acceptance_run": marker}),
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
