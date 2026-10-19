"""Check that the one-click fixture stays local and enforces demo roles."""

import os
from unittest.mock import patch

import srj_local_simulation as simulation


def test_isolation_even_if_production_environment_exists():
    with patch.dict(os.environ, {
        "APP_ENV_FILE": "C:/sensitive/.env", "MONGO_URI": "mongodb+srv://not-used.invalid/",
        "ANTHROPIC_API_KEY": "not-used",
    }):
        app, db, credentials, product_id = simulation.build_fixture()
    assert app.config["MONGO_URI"] == "mongodb://127.0.0.1:1/"
    assert app.config["MONGO_DB"] == "srj_simulation_only"
    assert app.config["ANTHROPIC_API_KEY"] == ""
    assert db.users.count_documents({}) == 3
    assert len({value["password"] for value in credentials.values()}) == 3
    assert all(simulation.self_check(app, credentials, product_id).values())


def test_meta_does_not_disclose_credentials():
    app, _db, credentials, _product_id = simulation.build_fixture()
    with app.test_client() as client:
        response = client.get("/__srj_simulation_meta")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["scope"] == "loopback mongomock simulation"
    assert payload["atlas_contacted"] is False
    assert payload["named_acceptance"] is False
    assert all(entry["password"] not in response.get_data(as_text=True)
               for entry in credentials.values())


def test_local_demo_checkout_changes_only_memory_fixture():
    app, db, credentials, product_id = simulation.build_fixture()
    sku = db.product_skus.find_one({"product_id": product_id})
    with app.test_client() as client:
        client.get("/auth/login")
        with client.session_transaction() as browser_session:
            csrf = browser_session["csrf_token"]
        assert client.post("/auth/login", data={**credentials["REN"], "csrf_token": csrf}).status_code == 302
        client.get(f"/product/{product_id}")
        with client.session_transaction() as browser_session:
            csrf = browser_session["csrf_token"]
        added = client.post(f"/cart/add/{product_id}", json={"sku_id": str(sku["_id"]),
            "quantity": 2, "operation_id": "srj-local-add-001"},
            headers={"X-CSRF-Token": csrf})
        assert added.status_code == 200
        cart = db.carts.find_one({"status": "active"})
        assert cart is not None
        checkout = {"checkout_id": "srj-local-checkout-001", "cart_id": str(cart["_id"]),
            "expected_revision": cart["revision"]}
        first = client.post("/checkout", json=checkout, headers={"X-CSRF-Token": csrf})
        assert first.status_code == 200
        again = client.post("/checkout", json=checkout, headers={"X-CSRF-Token": csrf})
        assert again.status_code == 200
        assert db.orders.count_documents({}) == 1
        assert db.product_skus.find_one({"_id": sku["_id"]})["available_quantity"] == 8
