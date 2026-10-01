"""Offline route/service contracts. mongomock cannot verify MongoDB transactions."""
from decimal import Decimal
import pytest
import mongomock
from bson import ObjectId, Decimal128
from flask import g
from werkzeug.security import generate_password_hash
from app import create_app
from app.services.sku_gateway import CartService


class OfflineCart(CartService):
    def _run(self, callback):
        return callback(None)


@pytest.fixture
def shop():
    db = mongomock.MongoClient().test
    uid, pid, sid, category = (ObjectId() for _ in range(4))
    db.users.insert_one({"_id": uid, "schema_version": 4, "status": "active", "is_active": True,
                         "email": "test@example.test", "display_name": "測試會員", "role": "customer",
                         "password_hash": generate_password_hash("test-password")})
    db.products.insert_one({"_id": pid, "schema_version": 4, "product_code": "TEST", "product_name": "啞鈴",
                            "major_category_id": category, "minor_category_id": category, "category_path": ["sport", "weight"],
                            "status": "active", "average_rating_display": 4.0, "description": "重量訓練", "is_ai_recommendable": True})
    db.product_skus.insert_one({"_id": sid, "schema_version": 4, "product_id": pid, "sku_code": "TEST-1",
                                "variant_attributes": {"重量": "5kg"}, "status": "active", "price": Decimal128("10.25"),
                                "available_quantity": 10, "stock_quantity": 10, "reserved_quantity": 0, "safety_stock": 2})
    app = create_app({"TESTING": True, "SECRET_KEY": "offline-test-only", "DATA_MODE": "v4",
                      "CART_SERVICE_FACTORY": lambda db, **kw: OfflineCart(db, **kw),
                      "ENABLE_CHECKOUT": False, "AI_RECOMMENDATIONS_ENABLED": False, "AI_SUMMARY_ENABLED": False})

    @app.before_request
    def offline_database():
        g.db = db

    client = app.test_client()
    with client.session_transaction() as state:
        state.update(user_id=str(uid), role="customer", csrf_token="test-csrf")
    return app, client, db, uid, pid, sid


def post(client, path, **data):
    return client.post(path, json=data, headers={"X-CSRF-Token": "test-csrf"})


def test_add_update_remove_uses_skus_and_authenticated_owner(shop):
    app, client, db, uid, pid, sid = shop
    result = post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=2, operation_id="add-1", user_id=str(ObjectId()))
    assert result.status_code == 200
    cart = db.carts.find_one()
    assert cart["user_id"] == uid and cart["items"][0]["sku_id"] == sid
    assert db.behavior_events.find_one()["event_type"] == "ADD_TO_CART"
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=2, operation_id="add-1").status_code == 200
    assert db.cart_events.count_documents({}) == 1
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=3, operation_id="add-1").status_code == 409
    assert post(client, f"/cart/update/{sid}", quantity=3, operation_id="update-1").status_code == 200
    page = client.get("/cart")
    assert page.status_code == 200 and b"30.75" in page.data
    assert post(client, f"/cart/remove/{sid}", operation_id="remove-1").status_code == 200
    assert db.carts.find_one()["items"] == []
    with client.session_transaction() as state:
        assert "cart" not in state


@pytest.mark.parametrize("quantity", [0, -1, 100, True, 1.5, "2"])
def test_invalid_quantity_rejected(shop, quantity):
    _, client, db, _, pid, sid = shop
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=quantity, operation_id="bad").status_code == 400
    assert db.carts.count_documents({}) == 0


def test_missing_sku_wrong_product_and_csrf(shop):
    _, client, db, _, pid, sid = shop
    assert client.post(f"/cart/add/{pid}", json={}).status_code == 400
    assert post(client, f"/cart/add/{ObjectId()}", sku_id=str(sid), operation_id="wrong").status_code == 404
    assert post(client, f"/cart/add/{pid}", sku_id="invalid", operation_id="bad").status_code == 400
    assert db.carts.count_documents({}) == 0


def test_checkout_is_disabled_then_revision_checked_and_idempotent(shop):
    app, client, db, uid, pid, sid = shop
    post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=2, operation_id="add")
    cart = db.carts.find_one()
    data = {"cart_id": str(cart["_id"]), "expected_revision": cart["revision"], "checkout_id": "checkout-1"}
    assert post(client, "/checkout", **data).status_code == 403
    app.config["ENABLE_CHECKOUT"] = True
    assert post(client, "/checkout", **{**data, "expected_revision": 0}).status_code == 409
    assert post(client, "/checkout", **data).status_code == 200
    assert post(client, "/checkout", **data).status_code == 200
    assert db.orders.count_documents({}) == 1
    assert db.orders.find_one()["total_amount"].to_decimal() == Decimal("20.50")
    assert db.order_items.count_documents({}) == 1
    assert db.product_skus.find_one()["available_quantity"] == 8
    assert db.carts.find_one()["status"] == "converted"


def test_checkout_does_not_accept_other_users_cart(shop):
    app, client, db, uid, pid, sid = shop
    post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1, operation_id="add")
    cart = db.carts.find_one()
    other = ObjectId()
    db.users.insert_one({"_id": other, "schema_version": 4, "status": "active", "is_active": True})
    with client.session_transaction() as state:
        state["user_id"] = str(other)
    app.config["ENABLE_CHECKOUT"] = True
    assert post(client, "/checkout", cart_id=str(cart["_id"]), expected_revision=1, checkout_id="steal").status_code == 409
    assert db.orders.count_documents({}) == 0


def test_pages_render_sku_and_view_event(shop):
    _, client, db, uid, pid, sid = shop
    assert client.get("/").status_code == 200
    page = client.get(f"/product/{pid}")
    assert page.status_code == 200 and str(sid).encode() in page.data
    assert db.behavior_events.find_one()["event_type"] == "PRODUCT_VIEW"
    assert client.get("/cart").status_code == 200


def test_v4_login_and_registration(shop):
    _, client, db, _, _, _ = shop
    result = client.post("/auth/login", data={"csrf_token": "test-csrf", "email": "test@example.test", "password": "test-password"})
    assert result.status_code == 302
    with client.session_transaction() as state:
        assert state["name"] == "測試會員"
        state["csrf_token"] = "test-csrf"
    result = client.post("/auth/register", data={"csrf_token": "test-csrf", "email": "new@example.test", "password": "test-password", "name": "新會員"})
    assert result.status_code == 302
    user = db.users.find_one({"email": "new@example.test"})
    assert user["schema_version"] == 4 and user["status"] == "active"
    assert "name" not in user and user["preferences"]["budget_min"] is None


def test_revoked_member_and_admin_permissions(shop):
    _, client, db, uid, _, _ = shop
    with client.session_transaction() as state:
        state["role"] = "admin"
    assert client.get("/admin/").status_code == 302
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    assert client.get("/admin/").status_code == 200
    db.users.update_one({"_id": uid}, {"$set": {"status": "inactive", "is_active": False}})
    assert client.get("/cart").status_code == 302


def test_form_submission_and_missing_operation_key(shop):
    _, client, db, _, pid, sid = shop
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1).status_code == 400
    result = client.post(f"/cart/add/{pid}", data={"csrf_token": "test-csrf", "operation_id": "form-1", "sku_id": str(sid), "quantity": "2"})
    assert result.status_code == 303 and result.location == "/cart"
    assert db.carts.find_one()["items"][0]["quantity"] == 2


def test_admin_v4_decimal_metrics_and_summary_post(shop):
    _, client, db, uid, _, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    for payment, amount in [("paid", "123.45"), ("unpaid", "999.99"), ("refunded", "888.88")]:
        db.orders.insert_one({"order_number": payment, "payment_status": payment, "total_amount": Decimal128(amount), "status": "confirmed"})
    response = post(client, "/admin/summary")
    assert response.status_code == 200
    with client.application.test_request_context():
        g.db = db
        from app.admin import dashboard_data
        insights, _ = dashboard_data()
        assert insights["revenue"] == Decimal("123.45") and insights["orders"] == 1


def test_anonymous_cannot_mutate_and_database_failure_is_503(shop, monkeypatch):
    _, client, db, uid, pid, sid = shop
    with client.session_transaction() as state:
        state.pop("user_id")
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1, operation_id="x").status_code == 302
    from pymongo.errors import ConnectionFailure
    def unavailable(*args, **kwargs):
        raise ConnectionFailure("sensitive-host")
    monkeypatch.setattr(db.products, "find", unavailable)
    response = client.get("/")
    assert response.status_code == 503 and b"sensitive-host" not in response.data


def test_legacy_mode_still_renders_with_csrf():
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATA_MODE": "legacy"})
    db = mongomock.MongoClient().legacy
    db.products.insert_one({"name": "舊版商品", "is_active": True, "category": "測試", "price": 10, "stock": 2, "rating": 4})
    @app.before_request
    def inject():
        g.db = db
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert b"csrf_token" in client.get("/auth/login").data
    assert client.post("/auth/register", data={}).status_code == 400
