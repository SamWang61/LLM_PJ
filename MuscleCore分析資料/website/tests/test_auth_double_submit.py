"""J1 / #152 F01: a repeated login or logout submission must not show 400 when the first one already succeeded."""
import pytest
from test_v4_routes import shop


def fresh_client(app, token="pre-login-token"):
    client = app.test_client()
    with client.session_transaction() as state:
        state["csrf_token"] = token
    return client


def login(client, token="pre-login-token", next_path=None, password="test-password"):
    url = "/auth/login" + (f"?next={next_path}" if next_path else "")
    return client.post(url, data={"csrf_token": token, "email": "test@example.test", "password": password})


def test_second_login_click_lands_on_home_instead_of_400(shop):
    app, _, db, uid, _, _ = shop
    client = fresh_client(app)
    first = login(client)
    assert first.status_code == 302 and first.location == "/"
    second = login(client)  # same pre-login token; the session was cleared by the first login
    assert second.status_code == 302 and second.location == "/"
    assert client.get("/cart").status_code == 200  # still signed in


def test_second_login_for_admin_goes_to_dashboard_and_honours_local_next(shop):
    app, _, db, uid, _, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    client = fresh_client(app)
    login(client)
    assert login(client).location == "/admin/"
    client = fresh_client(app)
    login(client, next_path="/admin/recommendations")
    assert login(client, next_path="/admin/recommendations").location == "/admin/recommendations"
    assert login(client, next_path="//evil.example").location == "/admin/"


def test_second_logout_click_returns_home_instead_of_400(shop):
    app, client, _, _, _, _ = shop
    first = client.post("/auth/logout", data={"csrf_token": "test-csrf"})
    assert first.status_code == 302
    second = client.post("/auth/logout", data={"csrf_token": "test-csrf"})
    assert second.status_code == 302 and second.location == "/"
    assert "您已安全登出" in client.get("/").get_data(as_text=True)


def test_csrf_is_still_enforced_when_the_outcome_is_not_already_true(shop):
    app, client, _, _, pid, sid = shop
    # Signed in, but the token is missing or is not the one the earlier login used: still 400.
    assert client.post("/auth/login", data={"email": "test@example.test", "password": "test-password"}).status_code == 400
    assert client.post("/auth/login", data={"csrf_token": "guess", "email": "x", "password": "y"}).status_code == 400
    # Not signed in: a login with a wrong token is rejected.
    anonymous = fresh_client(app)
    assert anonymous.post("/auth/login", data={"csrf_token": "wrong", "email": "x", "password": "y"}).status_code == 400
    # Signed in: a logout without the right token is rejected and the session stays.
    assert client.post("/auth/logout", data={"csrf_token": "wrong"}).status_code == 400
    assert client.get("/cart").status_code == 200
    # Other forms are unaffected by the login/logout allowance.
    assert client.post(f"/cart/add/{pid}", data={"csrf_token": "wrong", "sku_id": str(sid), "quantity": 1}).status_code == 400


def test_repeat_with_a_different_old_token_is_rejected(shop):
    app, _, _, _, _, _ = shop
    client = fresh_client(app)
    login(client)
    assert login(client, token="another-old-token").status_code == 400
    with client.session_transaction() as state:
        assert "pre-login-token" not in str(dict(state))  # only a digest of the old token is kept


def test_wrong_password_on_repeat_is_not_turned_into_success(shop):
    app, _, _, _, _, _ = shop
    client = fresh_client(app)
    assert login(client, password="bad-password").status_code == 200  # form re-rendered with an error
    assert client.get("/cart").status_code == 302  # not signed in


def test_login_and_logout_forms_submit_once(shop):
    app, client, db, uid, _, _ = shop
    login_page = fresh_client(app).get("/auth/login").get_data(as_text=True)
    assert "data-single-submit" in login_page and "js/forms.js" in login_page
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    admin_page = client.get("/admin/").get_data(as_text=True)
    assert 'class="logout-form"' in admin_page and "data-single-submit" in admin_page and "js/forms.js" in admin_page
