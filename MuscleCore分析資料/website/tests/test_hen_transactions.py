"""Opt-in transactions on a local, disposable replica set only.

Set HEN_TEST_MONGO_URI to mongodb://127.0.0.1:<port>/?replicaSet=<name>.
This suite never uses .env or the production database. It drops only its own
randomly generated hen_acceptance_* database after the test.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from urllib.parse import urlsplit
import pytest
from bson import ObjectId, Decimal128
from pymongo import MongoClient
from app.services.sku_gateway import CartService, CartError, CartConflict
from app.services.member_sessions import advance_generation, generation, revoke_user_sessions


@pytest.fixture
def replica():
    uri = os.getenv("HEN_TEST_MONGO_URI")
    if not uri:
        pytest.skip("HEN_TEST_MONGO_URI absent; local replica set required")
    parsed = urlsplit(uri)
    if (parsed.scheme != "mongodb" or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.username or parsed.password or "," in parsed.netloc or parsed.path not in {"", "/"}):
        pytest.fail("Only a credential-free localhost replica set is permitted")
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    hello = client.admin.command("hello")
    assert hello.get("setName"), "Replica set required; standalone cannot verify transactions"
    name = "hen_acceptance_" + uuid4().hex
    db = client[name]
    # Existing idempotency indexes, without installing production migrations.
    db.carts.create_index([("user_id", 1)], unique=True, partialFilterExpression={"status": "active"})
    db.cart_events.create_index([("user_id", 1), ("operation_id", 1)], unique=True)
    db.orders.create_index([("user_id", 1), ("checkout_id", 1)], unique=True)
    db.behavior_events.create_index("event_id", unique=True)
    uid, pid, sid, category = (ObjectId() for _ in range(4))
    db.users.insert_one({"_id": uid, "schema_version": 4, "status": "active", "is_active": True})
    db.products.insert_one({"_id": pid, "schema_version": 4, "product_code": "LOCAL", "product_name": "隔離商品",
        "major_category_id": category, "minor_category_id": category, "status": "active"})
    db.product_skus.insert_one({"_id": sid, "product_id": pid, "status": "active", "price": Decimal128("10.25"),
        "available_quantity": 2, "stock_quantity": 2, "reserved_quantity": 0, "safety_stock": 0})
    try:
        yield db, uid, pid, sid
    finally:
        assert name.startswith("hen_acceptance_") and len(name) == len("hen_acceptance_") + 32
        client.drop_database(name)
        client.close()


def test_real_replay_and_rollback(replica):
    db, uid, pid, sid = replica
    service = CartService(db, enable_checkout=True)
    cart = service.add_item(uid, sid, 1, operation_id="add")
    class Failing(CartService):
        def _behavior(self, *args, **kwargs):
            raise RuntimeError("injected after stock/order writes")
    with pytest.raises(RuntimeError):
        Failing(db, enable_checkout=True).checkout_cart(uid, checkout_id="checkout",
            cart_id=cart["_id"], expected_revision=cart["revision"])
    assert db.orders.count_documents({}) == db.order_items.count_documents({}) == 0
    assert db.product_skus.find_one()["available_quantity"] == 2
    assert db.carts.find_one()["status"] == "active"
    result = service.checkout_cart(uid, checkout_id="checkout", cart_id=cart["_id"], expected_revision=cart["revision"])
    assert service.checkout_cart(uid, checkout_id="checkout", cart_id=cart["_id"], expected_revision=cart["revision"])["_id"] == result["_id"]
    assert db.orders.count_documents({}) == db.order_items.count_documents({}) == 1
    assert db.product_skus.find_one()["available_quantity"] == 1
    assert db.behavior_events.count_documents({"event_type": "PURCHASE"}) == 1


def test_real_concurrent_last_stock_cannot_oversell(replica):
    db, uid, pid, sid = replica
    service = CartService(db, enable_checkout=True)
    second = ObjectId()
    db.users.insert_one({"_id": second, "schema_version": 4, "status": "active", "is_active": True})
    carts = [service.add_item(user, sid, 1, operation_id="add") for user in (uid, second)]
    db.product_skus.update_one({"_id": sid}, {"$set": {"available_quantity": 1, "stock_quantity": 1}})
    from threading import Barrier
    barrier = Barrier(2)
    def checkout(pair):
        user, cart = pair
        barrier.wait(timeout=5)
        try:
            service.checkout_cart(user, checkout_id="checkout", cart_id=cart["_id"], expected_revision=cart["revision"])
            return "success"
        except (CartError, CartConflict):
            return "rejected"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(checkout, zip((uid, second), carts)))
    assert sorted(results) == ["rejected", "success"]
    assert db.orders.count_documents({}) == 1
    assert db.product_skus.find_one()["available_quantity"] == 0


def test_real_concurrent_login_generations_are_distinct(replica):
    db, uid, _, _ = replica
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda _: generation(advance_generation(db, uid)["last_login_at"]), range(4)))
    assert len(set(values)) == 4
    assert generation(db.users.find_one({"_id": uid})["last_login_at"]) == max(values)


def test_real_admin_transaction_can_rollback_revocation(replica):
    db, uid, _, _ = replica
    before = generation(advance_generation(db, uid)["last_login_at"])
    with db.client.start_session() as mongo_session:
        mongo_session.start_transaction()
        assert revoke_user_sessions(db, uid, mongo_session=mongo_session)
        db.users.update_one({"_id": uid}, {"$set": {"status": "inactive", "is_active": False}}, session=mongo_session)
        mongo_session.abort_transaction()
    user = db.users.find_one({"_id": uid})
    assert generation(user["last_login_at"]) == before and user["is_active"] is True
