"""REN's four member-event routes and their attribution boundary."""
from bson import ObjectId

from app.services.behavior_scope import production_events
from test_v4_routes import shop, post


def test_four_member_events_keep_identity_replay_and_demo_boundaries(shop):
    app, member, db, uid, pid, sid = shop
    app.config.update(BEHAVIOR_SYNTHETIC_BATCH="", ENABLE_CHECKOUT=True)
    anonymous = app.test_client()

    assert anonymous.get("/?q=training").status_code == 200
    assert anonymous.get(f"/product/{pid}").status_code == 200
    assert db.behavior_events.count_documents({}) == 0

    assert member.get("/?q=training").status_code == 200
    assert member.get(f"/product/{pid}").status_code == 200
    assert post(member, f"/cart/add/{pid}", sku_id=str(sid), quantity=2,
                operation_id="event-add", synthetic=True).status_code == 200
    cart = db.carts.find_one()
    assert post(member, f"/cart/add/{pid}", sku_id=str(sid), quantity=2,
                operation_id="event-add").status_code == 200
    checkout = dict(cart_id=str(cart["_id"]), expected_revision=1,
                    checkout_id="event-checkout")
    assert post(member, "/checkout", **checkout).status_code == 200
    assert post(member, "/checkout", **checkout).status_code == 200

    events = list(db.behavior_events.find().sort("event_at", 1))
    by_type = {event["event_type"]: event for event in events}
    assert len(events) == len(by_type) == 4
    assert set(by_type) == {"SEARCH", "PRODUCT_VIEW", "ADD_TO_CART", "PURCHASE"}
    assert len({event["event_id"] for event in events}) == 4
    assert all(event["user_id"] == uid and event["schema_version"] == 4
               and event["anonymous_id"] is None for event in events)

    search = by_type["SEARCH"]
    assert search["search_query"] == "training" and search["product_id"] is None
    assert search["metadata"] == {}
    view = by_type["PRODUCT_VIEW"]
    assert view["product_id"] == pid and view["quantity"] == 1
    assert view["metadata"] == {}
    add = by_type["ADD_TO_CART"]
    assert add["product_id"] == pid and add["cart_id"] == cart["_id"]
    assert add["quantity"] == 2 and add["order_id"] is None
    assert add["metadata"] == {}  # Client-supplied synthetic=True cannot change server policy.
    purchase = by_type["PURCHASE"]
    assert purchase["product_id"] == pid and purchase["cart_id"] == cart["_id"]
    assert purchase["order_id"] == db.orders.find_one()["_id"]
    assert purchase["quantity"] == 2
    assert purchase["metadata"] == {"demo_checkout": True,
                                    "exclude_from_attribution": True}
    assert {event["event_type"] for event in production_events(events)} == {
        "SEARCH", "PRODUCT_VIEW", "ADD_TO_CART"}


def test_rejected_cart_mutation_does_not_create_member_event(shop):
    _, member, db, _, pid, sid = shop
    assert post(member, f"/cart/add/{ObjectId()}", sku_id=str(sid),
                operation_id="wrong-product").status_code == 404
    assert post(member, f"/cart/add/{pid}", sku_id=str(sid), quantity=0,
                operation_id="bad-quantity").status_code == 400
    assert db.behavior_events.count_documents({}) == 0
