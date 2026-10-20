"""Read-only product, order and member lists (design spec 6.1–6.3)."""
from datetime import datetime
import pytest
from bson import Decimal128, ObjectId
from test_v4_routes import shop
from app.services.admin_records import mask_email


@pytest.fixture
def admin(shop):
    app, client, db, uid, pid, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    return app, client, db, uid, pid, sid


def page(client, url, status=200):
    response = client.get(url)
    assert response.status_code == status, response.status_code
    return response.get_data(as_text=True)


def add_order(db, number, at, user_id=None, **extra):
    document = {"order_number": number, "ordered_at": datetime.fromisoformat(at), "status": "confirmed",
                "payment_status": "paid", "shipping_status": "processing", "is_demo": False,
                "subtotal": Decimal128("100.00"), "discount_amount": Decimal128("10.00"),
                "shipping_fee": Decimal128("5.00"), "total_amount": Decimal128("95.00"), "user_id": user_id, **extra}
    return db.orders.insert_one(document).inserted_id


# ---------- products ----------

def test_product_list_aggregates_skus_and_filters(admin):
    _, client, db, _, pid, sid = admin
    major = db.categories.insert_one({"name": "重訓器材", "level": 1}).inserted_id
    db.products.update_one({"_id": pid}, {"$set": {"major_category_id": major, "image_urls": ["https://img.example.test/a.jpg"],
                                                   "rating_count": 3}})
    db.product_skus.insert_many([
        {"product_id": pid, "sku_code": "TEST-2", "status": "active", "price": Decimal128("8.00"), "available_quantity": 4},
        {"product_id": pid, "sku_code": "TEST-3", "status": "inactive", "price": Decimal128("1.00"), "available_quantity": 9},
        {"product_id": pid, "sku_code": "TEST-4", "status": "active", "price": Decimal128("2.00"), "available_quantity": 0}])
    other = db.products.insert_one({"product_code": "ZZZ", "product_name": "瑜珈墊", "status": "draft", "is_ai_recommendable": False}).inserted_id
    html = page(client, "/admin/products")
    assert "啞鈴" in html and "瑜珈墊" in html and "重訓器材" in html and "https://img.example.test/a.jpg" in html
    assert '<td class="num">4</td>' in html and '<td class="num">14</td>' in html  # 4 SKUs; available 10+4 from active only
    assert "NT$ 8.00" in html and "NT$ 1.00" not in html and "NT$ 2.00" not in html  # lowest sellable price only
    assert "4.0（3）" in html and "草稿" in html
    assert "瑜珈墊" not in page(client, f"/admin/products?major={major}")
    assert "啞鈴" not in page(client, "/admin/products?status=draft")
    assert "瑜珈墊" not in page(client, "/admin/products?recommendable=yes")
    assert "瑜珈墊" in page(client, "/admin/products?q=zz") and "啞鈴" not in page(client, "/admin/products?q=zz")
    assert str(other)  # keep reference


def test_product_keyword_is_literal_not_regex(admin):
    _, client, _, _, _, _ = admin
    assert "沒有符合條件的商品" in page(client, "/admin/products?q=.*")
    page(client, "/admin/products?q=%28%5B")  # "([" must not raise a regex error


@pytest.mark.parametrize("query", ["status=deleted", "recommendable=maybe", "major=not-an-id", "page=0", "page=x", "q=" + "a" * 51])
def test_product_invalid_filters_return_400_with_back_link(admin, query):
    _, client, _, _, _, _ = admin
    html = page(client, f"/admin/products?{query}", status=400)
    assert 'role="alert"' in html and "返回商品管理" in html and 'href="/admin/products"' in html


def test_product_pagination(admin, monkeypatch):
    _, client, db, _, _, _ = admin
    monkeypatch.setattr("app.services.admin_catalog.PAGE_SIZE", 2)
    for n in range(3):
        db.products.insert_one({"product_code": f"P{n}", "product_name": f"商品{n}", "status": "active", "is_ai_recommendable": True})
    first = page(client, "/admin/products?q=P")
    assert "共 3 筆 · 第 1／2 頁" in first and "page=2" in first and "上一頁" not in first
    second = page(client, "/admin/products?q=P&page=2")
    assert "商品2" in second and "上一頁" in second and "下一頁" not in second
    assert "第 2／2 頁" in page(client, "/admin/products?q=P&page=99")  # out of range clamps to last page


# ---------- orders ----------

def test_order_list_filters_by_taipei_date_demo_status_and_number(admin):
    _, client, db, _, _, _ = admin
    add_order(db, "VC-INSIDE", "2026-09-30T16:00:00+00:00")   # 10/01 00:00 Taipei
    add_order(db, "VC-BEFORE", "2026-09-30T15:59:59+00:00")   # 09/30 Taipei
    add_order(db, "VC-DEMO", "2026-10-01T03:00:00+00:00", is_demo=True)
    add_order(db, "VC-UNPAID", "2026-10-01T04:00:00+00:00", payment_status="unpaid", status="pending")
    html = page(client, "/admin/orders?start=2026-10-01&end=2026-10-01")
    assert "VC-INSIDE" in html and "VC-BEFORE" not in html and "2026-10-01 00:00" in html
    assert "VC-DEMO" not in page(client, "/admin/orders?start=2026-10-01&end=2026-10-01&demo=exclude")
    unpaid = page(client, "/admin/orders?payment=unpaid")
    assert "VC-UNPAID" in unpaid and "VC-INSIDE" not in unpaid
    assert "VC-UNPAID" in page(client, "/admin/orders?status=pending")
    by_number = page(client, "/admin/orders?number=demo")
    assert "VC-DEMO" in by_number and "VC-INSIDE" not in by_number


@pytest.mark.parametrize("query", ["start=2026-10-02&end=2026-10-01", "start=2026-10-01", "status=lost", "payment=free", "demo=maybe"])
def test_order_invalid_filters(admin, query):
    _, client, _, _, _, _ = admin
    assert "返回訂單管理" in page(client, f"/admin/orders?{query}", status=400)


def test_order_detail_shows_items_amounts_timeline_and_masked_member(admin):
    _, client, db, uid, pid, sid = admin
    oid = add_order(db, "VC-DETAIL", "2026-10-01T02:00:00+00:00", user_id=uid,
                    paid_at=datetime.fromisoformat("2026-10-01T02:05:00+00:00"))
    db.order_items.insert_one({"order_id": oid, "product_id": pid, "sku_id": sid, "product_name_snapshot": "快照啞鈴",
                               "product_code_snapshot": "TEST", "quantity": 2, "unit_price": Decimal128("50.00"),
                               "line_total": Decimal128("100.00")})
    html = page(client, f"/admin/orders/{oid}")
    assert "快照啞鈴" in html and "NT$ 50.00" in html and "NT$ 100.00" in html
    assert "NT$ 10.00" in html and "NT$ 5.00" in html and "NT$ 95.00" in html
    assert "2026-10-01 10:00" in html and "2026-10-01 10:05" in html and "完成" not in html.split("狀態時間軸")[1].split("</ol>")[0]
    assert "測試會員" in html and "t***@example.test" in html and "test@example.test" not in html
    assert "<form" not in html.split('class="admin-main"')[1]  # read-only: no write forms


def test_order_detail_404(admin):
    _, client, _, _, _, _ = admin
    page(client, "/admin/orders/not-an-id", status=404)
    page(client, f"/admin/orders/{ObjectId()}", status=404)


# ---------- members ----------

def test_member_list_masks_email_and_never_shows_password_hash(admin):
    _, client, db, _, _, _ = admin
    db.users.insert_one({"display_name": "王小明", "email": "ming@example.test", "role": "customer", "status": "inactive",
                         "is_active": False, "member_level": "gold", "password_hash": "pbkdf2:secret-hash",
                         "registered_at": datetime.fromisoformat("2026-10-01T02:00:00+00:00")})
    html = page(client, "/admin/members")
    assert "王小明" in html and "m***@example.test" in html and "ming@example.test" not in html
    assert "pbkdf2" not in html and "secret-hash" not in html and "password" not in html
    assert "gold" in html and "停用" in html and "2026-10-01 10:00" in html


def test_member_filters_and_email_not_searchable(admin):
    _, client, db, _, _, _ = admin
    db.users.insert_one({"display_name": "王小明", "email": "ming@example.test", "role": "customer", "status": "active"})
    assert "王小明" in page(client, "/admin/members?q=小明")
    assert "沒有符合條件的會員" in page(client, "/admin/members?q=ming%40example")
    customers = page(client, "/admin/members?role=customer").split("<tbody>")[1]
    assert "王小明" in customers and "測試會員" not in customers  # the fixture user is the admin
    assert "王小明" not in page(client, "/admin/members?status=inactive")
    assert "返回會員管理" in page(client, "/admin/members?role=root", status=400)


def test_member_list_has_no_deactivate_action_and_no_revoke_for_admins(admin):
    _, client, _, _, _, _ = admin
    html = page(client, "/admin/members")  # only the admin fixture user exists
    assert "管理員帳號不能從後台停用" in html and 'method="post"' not in html and "停用帳號" not in html


# ---------- revoke all device sessions (customers only; audit added with D5) ----------

def customer_with_sessions(app, db, count):
    from app.services.member_sessions import create_member_session
    cid = db.users.insert_one({"schema_version": 4, "display_name": "被撤銷會員", "email": "kick@example.test",
                               "role": "customer", "status": "active", "is_active": True,
                               "password_hash": "x"}).inserted_id
    with app.app_context():
        tokens = [create_member_session(db, db.users.find_one({"_id": cid})) for _ in range(count)]
    return cid, tokens


def revoke(client, user_id, csrf="test-csrf", **form):
    return client.post(f"/admin/members/{user_id}/revoke-sessions", data={"csrf_token": csrf, **form})


def test_revoke_signs_customer_out_of_every_device(admin):
    app, client, db, uid, _, _ = admin
    cid, tokens = customer_with_sessions(app, db, 2)
    assert 'action="/admin/members/%s/revoke-sessions"' % cid in page(client, "/admin/members")
    response = revoke(client, cid, q="被撤銷", role="customer")
    assert response.status_code == 302 and "/admin/members?" in response.location
    assert "q=" in response.location and "role=customer" in response.location
    assert db.auth_sessions.count_documents({"user_id": cid}) == 0
    assert db.auth_sessions.count_documents({"user_id": uid}) == 1  # the admin's own session is untouched
    assert "已撤銷 2 個裝置" in page(client, response.location)
    # The revoked customer's old session no longer reaches member pages.
    kicked = app.test_client()
    with kicked.session_transaction() as state:
        state.update(user_id=str(cid), role="customer", member_session=tokens[0], csrf_token="t")
    assert kicked.get("/cart").status_code == 302


def test_revoke_with_no_sessions_reports_zero(admin):
    app, client, db, _, _, _ = admin
    cid, _ = customer_with_sessions(app, db, 0)
    assert "已撤銷 0 個裝置" in page(client, revoke(client, cid).location)


def test_revoke_refuses_admin_accounts(admin):
    app, client, db, uid, _, _ = admin
    other_admin = db.users.insert_one({"schema_version": 4, "display_name": "另一位管理員", "role": "admin",
                                       "status": "active", "is_active": True}).inserted_id
    db.auth_sessions.insert_one({"_id": "x" * 64, "user_id": other_admin})
    assert revoke(client, other_admin).status_code == 403
    assert revoke(client, uid).status_code == 403  # including yourself
    assert db.auth_sessions.count_documents({"user_id": other_admin}) == 1
    assert db.auth_sessions.count_documents({"user_id": uid}) == 1


def test_revoke_requires_csrf_and_existing_member(admin):
    app, client, db, _, _, _ = admin
    cid, _ = customer_with_sessions(app, db, 1)
    assert revoke(client, cid, csrf="wrong").status_code == 400
    assert db.auth_sessions.count_documents({"user_id": cid}) == 1
    assert revoke(client, ObjectId()).status_code == 404
    assert revoke(client, "not-an-id").status_code == 404


def test_revoke_requires_admin(shop):
    app, client, db, _, _, _ = shop
    cid, _ = customer_with_sessions(app, db, 1)
    assert revoke(client, cid).status_code == 302
    assert db.auth_sessions.count_documents({"user_id": cid}) == 1


@pytest.mark.parametrize("email,masked", [("ab@x.io", "a***@x.io"), ("", "—"), (None, "—"), ("no-at-sign", "—")])
def test_mask_email(email, masked):
    assert mask_email(email) == masked


def test_lists_require_admin(shop):
    _, client, _, _, _, _ = shop
    for url in ("/admin/products", "/admin/orders", f"/admin/orders/{ObjectId()}", "/admin/members"):
        assert client.get(url).status_code == 302
