"""Recommendation attribution (recommendation_logs): impressions, clicks, add-to-cart, purchases, monitor funnel."""
import re
from datetime import timedelta
import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError
from test_v4_routes import shop, post
from app.db import utcnow
from app.services import recommendation_logs as rec_logs


@pytest.fixture
def rated(shop):
    """The fixture product needs a real high rating to appear in the cold-start 6+4 list."""
    app, client, db, uid, pid, sid = shop
    db.products.update_one({"_id": pid}, {"$set": {"rating_status": "ACTUAL", "average_rating_display": 4.8,
                                                   "average_rating_raw": 4.8, "rating_count": 3}})
    return app, client, db, uid, pid, sid


def rec_link(html):
    match = re.search(r'href="/product/[0-9a-f]{24}\?rec=([0-9a-f]{32})"', html)
    return match.group(1) if match else None


def test_home_logs_impression_and_tags_links(rated):
    _, client, db, uid, pid, _ = rated
    html = client.get("/").get_data(as_text=True)
    log = db.recommendation_logs.find_one({"user_id": uid, "recommendation_type": "PERSONALIZED"})
    assert log and log["items"][0]["product_id"] == pid and log["items"][0]["position"] == 1
    assert isinstance(log["items"][0]["score"], float) and log["items"][0]["reason_code"] == "HIGH_RATING"
    assert log["clicked_product_ids"] == [] and log["schema_version"] == 4 and log["algorithm_version"]
    assert rec_link(html) == log["recommendation_id"]


def test_same_list_within_window_is_one_impression(rated):
    _, client, db, uid, _, _ = rated
    client.get("/")
    client.get("/recommendations")
    client.get("/")
    assert db.recommendation_logs.count_documents({"user_id": uid}) == 1
    db.recommendation_logs.update_many({}, {"$set": {"shown_at": utcnow() - timedelta(minutes=31)}})
    client.get("/")
    assert db.recommendation_logs.count_documents({"user_id": uid}) == 2


def test_click_and_add_to_cart_are_attributed(rated):
    _, client, db, uid, pid, sid = rated
    rec_id = rec_link(client.get("/").get_data(as_text=True))
    product_page = client.get(f"/product/{pid}?rec={rec_id}").get_data(as_text=True)
    assert f'name="rec" value="{rec_id}"' in product_page
    log = db.recommendation_logs.find_one({"recommendation_id": rec_id})
    assert log["clicked_product_ids"] == [pid]
    assert db.behavior_events.find_one({"event_type": "PRODUCT_VIEW"})["recommendation_id"] == rec_id
    response = post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1, operation_id="rec-add-1", rec=rec_id)
    assert response.status_code in (200, 303)
    assert db.recommendation_logs.find_one({"recommendation_id": rec_id})["added_to_cart_product_ids"] == [pid]


def test_forged_or_foreign_rec_ids_are_ignored(rated):
    app, client, db, uid, pid, _ = rated
    other = ObjectId()
    db.recommendation_logs.insert_one({"schema_version": 4, "user_id": other, "recommendation_id": "a" * 32,
                                       "recommendation_type": "PERSONALIZED", "algorithm_version": "x",
                                       "items": [{"product_id": pid, "position": 1, "score": 1.0, "reason_code": "X"}],
                                       "shown_at": utcnow(), "clicked_product_ids": [], "added_to_cart_product_ids": [],
                                       "purchased_product_ids": [], "created_at": utcnow()})
    for rec in ("a" * 32, "not-hex", "<script>"):
        html = client.get(f"/product/{pid}?rec={rec}").get_data(as_text=True)
        assert 'name="rec"' not in html
    assert db.recommendation_logs.find_one({"user_id": other})["clicked_product_ids"] == []
    with app.test_request_context():
        assert not rec_logs.record_click(db, {"_id": uid}, "b" * 32, pid)


def test_product_not_in_list_is_not_marked(rated):
    _, client, db, uid, pid, _ = rated
    rec_id = rec_link(client.get("/").get_data(as_text=True))
    base = db.products.find_one({"_id": pid})
    stranger = db.products.insert_one({**{k: v for k, v in base.items() if k != "_id"}, "product_code": "OTHER",
                                       "product_name": "別的商品"}).inserted_id
    client.get(f"/product/{stranger}?rec={rec_id}")
    assert db.recommendation_logs.find_one({"recommendation_id": rec_id})["clicked_product_ids"] == []


def test_anonymous_and_synthetic_runs_are_not_logged(rated):
    app, client, db, uid, _, _ = rated
    with client.session_transaction() as state:
        state.pop("user_id")
    assert rec_link(client.get("/").get_data(as_text=True)) is None
    assert db.recommendation_logs.count_documents({}) == 0
    with client.session_transaction() as state:
        state["user_id"] = str(uid)
    app.config["BEHAVIOR_SYNTHETIC_BATCH"] = "test-batch"
    client.get("/")
    assert db.recommendation_logs.count_documents({}) == 0


def test_purchases_credit_only_real_orders_after_add_to_cart(rated):
    app, _, db, uid, pid, _ = rated
    member = {"_id": uid}
    with app.test_request_context():
        rec_id = rec_logs.log_impressions(db, member, {"personalized": [{"product": {"_id": pid}, "score": 2, "reason": "真實高星商品"}],
                                                       "source": "rules"})["personalized"]
        assert rec_logs.record_purchases(db, member, {"is_demo": False}, [pid]) == 0  # not added to cart yet
        rec_logs.record_add_to_cart(db, member, rec_id, pid)
        assert rec_logs.record_purchases(db, member, {"is_demo": True}, [pid]) == 0  # demo checkout never counts
        assert db.recommendation_logs.find_one({"recommendation_id": rec_id})["purchased_product_ids"] == []
        assert rec_logs.record_purchases(db, member, {"is_demo": False}, [pid]) == 1
    assert db.recommendation_logs.find_one({"recommendation_id": rec_id})["purchased_product_ids"] == [pid]


def test_logging_failure_does_not_break_pages(rated, monkeypatch):
    _, client, db, _, pid, _ = rated
    def broken(*args, **kwargs):
        raise PyMongoError("log store down")
    monkeypatch.setattr(db.recommendation_logs, "insert_one", broken)
    response = client.get("/")
    assert response.status_code == 200 and rec_link(response.get_data(as_text=True)) is None
    monkeypatch.setattr(db.recommendation_logs, "update_one", broken)
    assert client.get(f"/product/{pid}?rec={'c' * 32}").status_code == 200


def test_monitor_shows_funnel(rated):
    _, client, db, uid, pid, sid = rated
    rec_id = rec_link(client.get("/").get_data(as_text=True))
    client.get(f"/product/{pid}?rec={rec_id}")
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    html = client.get("/admin/recommendations").get_data(as_text=True)
    assert "推薦成效（最近 30 天）" in html and "示範結帳不計入成效" in html
    row = html.split("依你的喜好（6）")[1].split("</tr>")[0]
    assert re.findall(r'<td class="num">([^<]+)</td>', row)[:7] == ["1", "1", "1", "0", "0", "100.0%", "0.0%"]


def test_monitor_empty_state(shop):
    _, client, db, uid, _, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    assert "還沒有推薦紀錄" in client.get("/admin/recommendations").get_data(as_text=True)


def test_intervening_list_does_not_reset_the_dedupe_window(rated):
    app, _, db, uid, pid, _ = rated
    other = ObjectId()
    def block(ids):
        return {"source": "rules", "personalized": [
            {"product": {"_id": item}, "score": 1, "reason": "可售商品探索"} for item in ids]}
    with app.app_context():
        first = rec_logs.log_impressions(db, {"_id": uid}, block([pid, other]))
        reordered = rec_logs.log_impressions(db, {"_id": uid}, block([other, pid]))
        last = rec_logs.log_impressions(db, {"_id": uid}, block([pid, other]))
    assert last == first and reordered != first
    assert db.recommendation_logs.count_documents({"user_id": uid}) == 2


@pytest.mark.parametrize("skip", [None, "demo", "synthetic"])
def test_attribution_reads_cannot_fail_an_already_committed_checkout(shop, monkeypatch, skip):
    from types import SimpleNamespace
    from pymongo.errors import ConnectionFailure
    from app import store_v4
    app, client, db, uid, pid, sid = shop
    app.config["ENABLE_CHECKOUT"] = True
    assert post(client, f"/cart/add/{pid}", sku_id=str(sid), quantity=1,
                operation_id="attribution-read-add").status_code == 200
    cart = db.carts.find_one({"user_id": uid})
    checkout_factory = store_v4.cart_service
    def committed_checkout(*args, **kwargs):
        order = checkout_factory().checkout_cart(*args, **kwargs)
        # Exercise real-order attribution without enabling real payment in the fixture.
        return {**order, "is_demo": skip == "demo"}
    monkeypatch.setattr(store_v4, "cart_service", lambda: SimpleNamespace(checkout_cart=committed_checkout))
    if skip == "synthetic":
        app.config["BEHAVIOR_SYNTHETIC_BATCH"] = "isolated-attribution-test"
    reads = []
    def unavailable(*args, **kwargs):
        reads.append(True)
        if skip:
            raise AssertionError("disabled attribution must not query order items")
        raise ConnectionFailure("isolated optional read failure")
    monkeypatch.setattr(db.order_items, "find", unavailable)
    response = post(client, "/checkout", checkout_id="attribution-read-checkout",
                    cart_id=str(cart["_id"]), expected_revision=cart["revision"])
    assert response.status_code == 200
    assert db.orders.count_documents({"user_id": uid}) == 1
    assert len(reads) == (0 if skip else 1)
