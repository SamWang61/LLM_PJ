"""Disposable, loopback-only VibeCart exercise for SAM, REN, and JEFF.

This is a visual/process simulation, not a MongoDB transaction, production
deployment, physical-phone test, off-device restore, or named acceptance.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from unittest.mock import patch
import webbrowser

import mongomock
from bson import Decimal128, ObjectId
from flask import g, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "MuscleCore分析資料" / "website"))
from app import create_app  # noqa: E402
from app.services.sku_gateway import CartService  # noqa: E402


class SimulatedCart(CartService):
    def _run(self, callback):
        # mongomock has no real transaction. Never claim rollback acceptance.
        return callback(None)


def build_fixture():
    db = mongomock.MongoClient().srj_simulation_only
    credentials = {}
    for role, app_role in (("SAM", "admin"), ("REN", "customer"), ("JEFF", "admin")):
        user_id = ObjectId()
        password = secrets.token_urlsafe(18)
        email = f"{role.lower()}-local@example.invalid"
        db.users.insert_one({"_id": user_id, "schema_version": 4, "status": "active",
            "is_active": True, "role": app_role, "email": email,
            "display_name": f"{role} 本機模擬", "password_hash": generate_password_hash(password)})
        credentials[role] = {"email": email, "password": password}

    product_id, sku_id, category_id = (ObjectId() for _ in range(3))
    db.products.insert_one({"_id": product_id, "schema_version": 4, "status": "active",
        "product_code": "SRJ-LOCAL", "product_name": "隔離模擬商品",
        "major_category_id": category_id, "minor_category_id": category_id,
        "category_path": ["local", "simulation"], "average_rating_display": 4.0,
        "description": "僅在本機記憶體，不連正式資料庫。"})
    db.product_skus.insert_one({"_id": sku_id, "schema_version": 4, "product_id": product_id,
        "status": "active", "sku_code": "SRJ-LOCAL-1",
        "variant_attributes": {"規格": "1件"}, "price": Decimal128("10.25"),
        "stock_quantity": 10, "available_quantity": 10,
        "reserved_quantity": 0, "safety_stock": 0})

    # Do not load the checkout's .env or any production key/connection string.
    clean_env = {name: "" for name in ("APP_ENV_FILE", "MONGO_URI", "ANTHROPIC_API_KEY")}
    with patch.dict(os.environ, clean_env), patch("app.load_dotenv", lambda *args, **kwargs: False):
        app = create_app({"TESTING": True, "SECRET_KEY": secrets.token_urlsafe(32),
            "DATA_MODE": "v4", "ENABLE_CHECKOUT": True,
            "CART_SERVICE_FACTORY": lambda database, **kwargs: SimulatedCart(database, **kwargs),
            "AI_RECOMMENDATIONS_ENABLED": False, "AI_SUMMARY_ENABLED": False,
            "AI_FREE_QUESTION_ENABLED": False, "MONGO_URI": "mongodb://127.0.0.1:1/",
            "MONGO_DB": "srj_simulation_only"})

    @app.before_request
    def attach_fixture():
        g.db = db

    @app.get("/__srj_simulation_meta")
    def simulation_meta():
        return jsonify({"scope": "loopback mongomock simulation", "product_id": str(product_id),
            "atlas_contacted": False, "physical_device": False, "named_acceptance": False})

    return app, db, credentials, product_id


def self_check(app, credentials, product_id):
    checks = {}
    for role in ("SAM", "REN", "JEFF"):
        with app.test_client() as client:
            client.get("/auth/login")
            with client.session_transaction() as browser_session:
                csrf = browser_session["csrf_token"]
            login = client.post("/auth/login", data={**credentials[role], "csrf_token": csrf},
                follow_redirects=True)
            checks[f"{role}_login"] = login.status_code == 200 and "帳號或密碼不正確" not in login.get_data(as_text=True)
            admin = client.get("/admin/", follow_redirects=False)
            checks[f"{role}_admin_policy"] = admin.status_code == 200 if role != "REN" else admin.status_code in (302, 303)
            checks[f"{role}_product"] = client.get(f"/product/{product_id}").status_code == 200
            checks[f"{role}_cart"] = client.get("/cart").status_code == 200
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=("SAM", "REN", "JEFF"))
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    app, _db, credentials, product_id = build_fixture()
    checks = self_check(app, credentials, product_id)
    if not all(checks.values()):
        print(json.dumps({"scope": "loopback mongomock simulation", "checks": checks}), file=sys.stderr)
        return 1
    if args.self_check:
        print(json.dumps({"status": "passed", "scope": "loopback mongomock simulation",
            "checks": checks, "atlas_contacted": False, "named_acceptance": False}))
        return 0

    server = make_server("127.0.0.1", 0, app, threaded=True)
    url = f"http://127.0.0.1:{server.server_port}/auth/login"
    print("\n=== VibeCart 單機模擬環境 ===")
    print("僅供流程演練；記憶體資料庫，未連正式 Atlas，無真交易／實機／本人簽收。")
    print("角色:", args.role, "\n網址:", url)
    print("本次一次性帳號:", credentials[args.role]["email"])
    print("本次一次性密碼:", credentials[args.role]["password"])
    print("關閉此視窗或按 Ctrl+C 即停止，記憶體資料隨程序消失。\n", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
