"""REN acceptance cases with isolated mongomock; not transaction proof."""
from datetime import datetime, timezone
import pytest
from bson import ObjectId, Decimal128
from test_v4_routes import shop, post
from app.services.member_sessions import revoke_user_sessions, create_member_session


def cookie(client):
    return client.get_cookie("session").value


def replay(app, value):
    other = app.test_client()
    other.set_cookie("session", value)
    return other


def login(client, email="test@example.test", password="test-password"):
    client.get("/auth/login")
    with client.session_transaction() as state:
        token = state["csrf_token"]
    return client.post("/auth/login", data={"csrf_token": token, "email": email, "password": password})


def test_v4_cart_login_returns_to_cart_and_rejects_external_next(shop):
    app, _, _, _, _, _ = shop
    member = app.test_client()
    redirected = member.get("/cart")
    assert redirected.status_code == 302 and redirected.location == "/auth/login?next=/cart"
    page = member.get(redirected.location)
    assert "登入｜VibeCart" in page.get_data(as_text=True)
    with member.session_transaction() as state:
        csrf = state["csrf_token"]
    result = member.post(redirected.location, data={
        "csrf_token": csrf, "email": "test@example.test", "password": "test-password"})
    assert result.status_code == 302 and result.location == "/cart"
    assert member.get(result.location).status_code == 200
    register = member.get("/auth/register").get_data(as_text=True)
    assert "加入會員｜VibeCart" in register and "JOIN VIBECART" in register

    outside = app.test_client()
    outside.get("/auth/login")
    with outside.session_transaction() as state:
        csrf = state["csrf_token"]
    result = outside.post("/auth/login?next=%2F%2Fevil.example", data={
        "csrf_token": csrf, "email": "test@example.test", "password": "test-password"})
    assert result.status_code == 302 and result.location == "/"


def test_logout_csrf_and_copied_cookie_cannot_replay(shop):
    app, client, db, uid, _, _ = shop
    old = cookie(client)
    assert client.get("/auth/logout").status_code == 200
    assert client.get("/cart").status_code == 200  # GET does not log out
    assert client.post("/auth/logout").status_code == 400
    assert post(client, "/auth/logout").status_code == 302
    assert replay(app, old).get("/cart").status_code == 302
    assert login(client).status_code == 302
    assert replay(app, old).get("/cart").status_code == 302


def test_two_devices_can_login_and_logout_independently(shop):
    app, client, db, uid, _, _ = shop
    old = cookie(client)
    second = app.test_client()
    assert login(second).status_code == 302
    assert replay(app, old).get("/cart").status_code == 200
    second_cookie = cookie(second)
    with second.session_transaction() as state:
        state["csrf_token"] = "test-csrf"
    assert post(second, "/auth/logout").status_code == 302
    assert replay(app, second_cookie).get("/cart").status_code == 302
    assert replay(app, old).get("/cart").status_code == 200
    assert revoke_user_sessions(db, uid)
    assert replay(app, old).get("/cart").status_code == 302


def test_same_browser_relogin_retires_previous_cookie_only(shop):
    app, client, db, uid, _, _ = shop
    previous_cookie = cookie(client)
    second_device = app.test_client()
    assert login(second_device).status_code == 302
    second_cookie = cookie(second_device)

    assert login(client).status_code == 302
    current_cookie = cookie(client)
    assert current_cookie != previous_cookie
    assert replay(app, previous_cookie).get("/cart").status_code == 302
    assert replay(app, current_cookie).get("/cart").status_code == 200
    assert replay(app, second_cookie).get("/cart").status_code == 200
    with client.session_transaction() as state:
        state["csrf_token"] = "test-csrf"
    assert post(client, "/auth/logout").status_code == 302
    assert replay(app, current_cookie).get("/cart").status_code == 302
    assert replay(app, second_cookie).get("/cart").status_code == 200


def test_disabled_then_reenabled_does_not_restore_revoked_cookie(shop):
    app, client, db, uid, pid, _ = shop
    old = cookie(client)
    db.users.update_one({"_id": uid}, {"$set": {"status": "inactive", "is_active": False}})
    assert client.get(f"/product/{pid}").status_code == 200
    assert db.behavior_events.count_documents({}) == 0
    assert replay(app, old).get("/cart").status_code == 302
    assert login(client).status_code == 200
    revoke_user_sessions(db, uid)
    db.users.update_one({"_id": uid}, {"$set": {"status": "active", "is_active": True}})
    assert replay(app, old).get("/cart").status_code == 302


def test_role_is_live_and_forged_cookie_role_cannot_authorize(shop):
    app, client, db, uid, _, _ = shop
    with client.session_transaction() as state:
        state["role"] = "admin"
    assert client.get("/admin/").status_code == 302
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    assert login(client).status_code == 302
    assert client.get("/admin/").status_code == 200
    old = cookie(client)
    db.users.update_one({"_id": uid}, {"$set": {"role": "customer"}})
    assert replay(app, old).get("/admin/").status_code == 302
    client.get("/cart")
    with client.session_transaction() as state:
        assert state["role"] == "customer"


def test_pre_generation_and_malformed_identity_fail_closed(shop):
    app, client, db, uid, _, _ = shop
    with client.session_transaction() as state:
        state.pop("member_session")
    assert client.get("/cart").status_code == 302
    with client.session_transaction() as state:
        state.update(user_id="not-an-id", member_session="invalid")
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("data", [
    {"name": "x", "email": "ok@example.test", "password": "test-password"},
    {"name": "會員", "email": "a@@example.test", "password": "test-password"},
    {"name": "會員", "email": "a@example", "password": "test-password"},
    {"name": "會員", "email": "a@example.test", "password": "short"},
])
def test_registration_invalid_does_not_write(shop, data):
    _, client, db, _, _, _ = shop
    response = client.post("/auth/register", data={"csrf_token": "test-csrf", **data})
    assert response.status_code == 400 and db.users.count_documents({}) == 1


def test_duplicate_email_and_registration_role_allowlist(shop):
    _, client, db, _, _, _ = shop
    data = {"csrf_token": "test-csrf", "name": "會員", "email": "TEST@example.test", "password": "test-password"}
    assert client.post("/auth/register", data=data).status_code == 409
    data.update(email="new@example.test", role="admin", is_active=False)
    assert client.post("/auth/register", data=data).status_code == 302
    assert db.users.find_one({"email": "new@example.test"})["role"] == "customer"


def test_bad_password_cannot_create_identity(shop):
    app, client, db, uid, _, _ = shop
    fresh = app.test_client()
    assert login(fresh, password="incorrect-password").status_code == 200
    with fresh.session_transaction() as state:
        assert "user_id" not in state
    assert fresh.get("/cart").status_code == 302


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login", "/auth/logout"])
def test_all_member_mutations_require_csrf(shop, path):
    _, client, db, _, _, _ = shop
    assert client.post(path, data={"email": "test@example.test", "password": "test-password"}).status_code == 400
    assert db.users.count_documents({}) == 1


def test_registration_unique_index_race_returns_409(shop, monkeypatch):
    _, client, db, _, _, _ = shop
    from pymongo.errors import DuplicateKeyError
    def duplicate(*args, **kwargs):
        raise DuplicateKeyError("duplicate")
    monkeypatch.setattr(db.users, "insert_one", duplicate)
    result = client.post("/auth/register", data={"csrf_token": "test-csrf", "name": "會員",
        "email": "new@example.test", "password": "test-password"})
    assert result.status_code == 409


def test_v4_login_does_not_publish_legacy_demo_credentials(shop):
    _, client, _, _, _, _ = shop
    page = client.get("/auth/login")
    assert "Demo123!" not in page.text and "Admin123!" not in page.text


def test_session_expiry_and_digest_only_storage(shop):
    from datetime import timedelta
    app, client, db, uid, _, _ = shop
    with client.session_transaction() as state:
        token = state["member_session"]
    row = db.auth_sessions.find_one()
    assert row["_id"] != token and token not in str(row)
    db.auth_sessions.update_one({"_id": row["_id"]}, {"$set": {"expires_at": datetime.now(timezone.utc)-timedelta(seconds=1)}})
    assert client.get("/cart").status_code == 302


def test_auth_database_failure_is_sanitized(shop, monkeypatch):
    _, client, db, _, _, _ = shop
    from pymongo.errors import ConnectionFailure
    def fail(*a, **k):
        raise ConnectionFailure("private-host-secret")
    monkeypatch.setattr(db.users, "find_one", fail)
    response = client.get("/cart")
    assert response.status_code == 503 and "private-host-secret" not in response.text


def test_two_cart_forms_revision_conflict_and_replay(shop):
    _, client, db, uid, pid, sid = shop
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1, operation_id="a").status_code == 200
    data = dict(quantity=2, operation_id="u", expected_revision=1)
    assert post(client, f"/cart/update/{sid}", **data).status_code == 200
    assert post(client, f"/cart/update/{sid}", **data).status_code == 200
    assert post(client, f"/cart/update/{sid}", **{**data, "expected_revision": 2}).status_code == 409
    assert post(client, f"/cart/remove/{sid}", operation_id="r", expected_revision=1).status_code == 409
    assert db.carts.find_one()["items"][0]["quantity"] == 2
    assert 'name="expected_revision" value="2"' in client.get("/cart").text


@pytest.mark.parametrize("revision", [True, -1, "1", 1.5])
def test_revision_types_rejected(shop, revision):
    _, client, db, _, pid, sid = shop
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1,
                operation_id="x", expected_revision=revision).status_code == 400
    assert db.carts.count_documents({}) == 0


@pytest.mark.parametrize("change", ["product", "sku", "stock"])
def test_checkout_revalidates_sellable_and_stock(shop, change):
    app, client, db, uid, pid, sid = shop
    post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=2, operation_id="a")
    cart = db.carts.find_one()
    if change == "product": db.products.update_one({"_id": pid}, {"$set": {"status": "inactive"}})
    if change == "sku": db.product_skus.update_one({"_id": sid}, {"$set": {"status": "inactive"}})
    if change == "stock": db.product_skus.update_one({"_id": sid}, {"$set": {"available_quantity": 1}})
    app.config["ENABLE_CHECKOUT"] = True
    assert post(client, "/checkout", cart_id=str(cart["_id"]), expected_revision=1, checkout_id="c").status_code == 400
    assert db.orders.count_documents({}) == 0


def test_checkout_reprices_ignores_client_money_and_rejects_changed_payload(shop):
    app, client, db, uid, pid, sid = shop
    post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=2, operation_id="a")
    cart = db.carts.find_one()
    db.product_skus.update_one({"_id": sid}, {"$set": {"price": Decimal128("12.50")}})
    app.config["ENABLE_CHECKOUT"] = True
    data = dict(cart_id=str(cart["_id"]), expected_revision=1, checkout_id="c", total_amount="0", user_id=str(ObjectId()))
    first = post(client, "/checkout", **data)
    assert first.status_code == 200
    assert post(client, "/checkout", **data).json == first.json
    assert post(client, "/checkout", **{**data, "expected_revision": 2}).status_code == 409
    assert post(client, "/checkout", **{**data, "cart_id": str(ObjectId())}).status_code == 409
    assert db.orders.count_documents({}) == 1
    assert db.orders.find_one()["total_amount"].to_decimal() == 25
    assert db.product_skus.find_one()["available_quantity"] == 8
    assert db.behavior_events.count_documents({"event_type": "PURCHASE"}) == 1
    assert db.behavior_events.find_one({"event_type": "PURCHASE"})["metadata"]["exclude_from_attribution"] is True


def test_all_four_events_are_server_marked_synthetic(shop):
    app, client, db, uid, pid, sid = shop
    app.config.update(BEHAVIOR_SYNTHETIC_BATCH="ren-offline-20261014", ENABLE_CHECKOUT=True)
    assert client.get("/?q=test").status_code == 200
    assert client.get(f"/product/{pid}").status_code == 200
    post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1, operation_id="a", synthetic=False)
    cart = db.carts.find_one()
    post(client, "/checkout", cart_id=str(cart["_id"]), expected_revision=1, checkout_id="c")
    events = list(db.behavior_events.find())
    assert {e["event_type"] for e in events} == {"SEARCH", "PRODUCT_VIEW", "ADD_TO_CART", "PURCHASE"}
    assert all(e["metadata"]["synthetic"] and e["metadata"]["exclude_from_attribution"] for e in events)
    assert all(e["metadata"]["synthetic_batch_id"] == "ren-offline-20261014" for e in events)


def test_synthetic_exclusion_is_before_sort_limit(shop, monkeypatch):
    app, client, db, uid, pid, sid = shop
    db.behavior_events.insert_one({"user_id": uid, "event_at": datetime(2020,1,1), "metadata": {}, "event_type": "SEARCH"})
    db.behavior_events.insert_many([{"user_id": uid, "event_at": datetime(2026,1,1), "metadata": {"synthetic": True}} for _ in range(60)])
    from app import store_v4
    seen = []
    def inspect(products, events, rules, settings):
        seen.extend(events)
        return {"personalized": [], "cross_category": [], "source": "rules-6plus4"}
    monkeypatch.setattr(store_v4, "recommendations_6_4", inspect)
    assert client.get("/").status_code == 200
    assert len(seen) == 1 and seen[0]["event_type"] == "SEARCH"
