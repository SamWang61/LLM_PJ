"""Read-only order and member lists for the admin (design spec 6.2, 6.3).

Members never expose password_hash or full email addresses. Audited device revocation
is implemented separately in admin_sessions; broader D5 status edits remain pending.
"""
from bson import ObjectId
from bson.errors import InvalidId
from .admin_catalog import PAGE_SIZE, AdminListError, keyword_pattern, page_number, pagination
from .dashboard import DashboardFilterError, dashboard_filters
from .sku_gateway import money

ORDER_STATUSES = ("pending", "confirmed", "shipping", "completed", "cancelled")
PAYMENT_STATUSES = ("unpaid", "paid", "failed", "refunded")
ORDER_FIELDS = {"order_number": 1, "ordered_at": 1, "status": 1, "payment_status": 1, "shipping_status": 1,
                "is_demo": 1, "total_amount": 1}
MEMBER_FIELDS = {"display_name": 1, "email": 1, "role": 1, "member_level": 1, "status": 1, "is_active": 1,
                 "registered_at": 1, "last_login_at": 1}


def mask_email(email):
    """j***@example.com — enough to tell accounts apart without showing the address."""
    local, _, domain = (email or "").partition("@")
    if not local or not domain:
        return "—"
    return f"{local[0]}***@{domain}"


def order_filters(values):
    try:
        dates = dashboard_filters({"start": values.get("start", ""), "end": values.get("end", ""), "demo": values.get("demo", "all")})
    except DashboardFilterError as error:
        raise AdminListError(str(error)) from None
    status, payment = values.get("status", ""), values.get("payment", "")
    if status and status not in ORDER_STATUSES:
        raise AdminListError("訂單狀態篩選值無效。")
    if payment and payment not in PAYMENT_STATUSES:
        raise AdminListError("付款狀態篩選值無效。")
    number, pattern = keyword_pattern(values.get("number"), limit=64)
    query = {}
    if "after" in dates:
        query["ordered_at"] = {"$gte": dates["after"], "$lt": dates["before"]}
    if dates["demo"] != "all":
        query["is_demo"] = True if dates["demo"] == "only" else {"$ne": True}
    if status:
        query["status"] = status
    if payment:
        query["payment_status"] = payment
    if pattern:
        query["order_number"] = pattern
    form = {"start": dates["start"], "end": dates["end"], "demo": dates["demo"], "status": status,
            "payment": payment, "number": number}
    return query, form, page_number(values)


def order_list(db, values):
    query, form, page = order_filters(values)
    paging = pagination(db.orders.count_documents(query), page)
    orders = list(db.orders.find(query, ORDER_FIELDS).sort([("ordered_at", -1), ("_id", -1)])
                  .skip((paging["page"] - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    rows = [{"id": str(o["_id"]), "number": o.get("order_number", ""), "ordered_at": o.get("ordered_at"),
             "status": o.get("status", ""), "payment": o.get("payment_status", ""), "shipping": o.get("shipping_status", ""),
             "demo": bool(o.get("is_demo")), "total": money(o["total_amount"]) if "total_amount" in o else None} for o in orders]
    return {"rows": rows, "form": form, "paging": paging}


def order_detail(db, order_id):
    try:
        oid = ObjectId(order_id)
    except (InvalidId, TypeError):
        return None
    order = db.orders.find_one({"_id": oid}, {**ORDER_FIELDS, "user_id": 1, "subtotal": 1, "discount_amount": 1,
                                              "shipping_fee": 1, "paid_at": 1, "completed_at": 1})
    if not order:
        return None
    items = [{"name": i.get("product_name_snapshot", ""), "code": i.get("product_code_snapshot", ""),
              "unit_price": money(i["unit_price"]) if "unit_price" in i else None, "quantity": i.get("quantity", 0),
              "line_total": money(i["line_total"]) if "line_total" in i else None}
             for i in db.order_items.find({"order_id": oid}).sort([("_id", 1)])]
    member = db.users.find_one({"_id": order.get("user_id")}, {"display_name": 1, "email": 1}) if order.get("user_id") else None
    timeline = [(label, order.get(field)) for label, field in
                (("下單", "ordered_at"), ("付款", "paid_at"), ("完成", "completed_at")) if order.get(field)]
    amounts = {key: money(order[key]) for key in ("subtotal", "discount_amount", "shipping_fee", "total_amount") if key in order}
    return {"id": str(oid), "number": order.get("order_number", ""), "ordered_at": order.get("ordered_at"),
            "status": order.get("status", ""), "payment": order.get("payment_status", ""),
            "shipping": order.get("shipping_status", ""), "demo": bool(order.get("is_demo")), "items": items,
            "amounts": amounts, "timeline": timeline,
            "member": {"name": member.get("display_name", ""), "email": mask_email(member.get("email"))} if member else None}


def member_filters(values):
    keyword, pattern = keyword_pattern(values.get("q"))
    role, status = values.get("role", ""), values.get("status", "")
    if role and role not in {"customer", "admin"}:
        raise AdminListError("角色篩選值無效。")
    if status and status not in {"active", "inactive"}:
        raise AdminListError("狀態篩選值無效。")
    query = {}
    if pattern:
        # Search display names only; email is not searchable so the masked list cannot be used to probe addresses.
        query["display_name"] = pattern
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    return query, {"q": keyword, "role": role, "status": status}, page_number(values)


def member_list(db, values):
    query, form, page = member_filters(values)
    paging = pagination(db.users.count_documents(query), page)
    users = list(db.users.find(query, MEMBER_FIELDS).sort([("registered_at", -1), ("_id", -1)])
                 .skip((paging["page"] - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    rows = [{"id": str(u["_id"]), "name": u.get("display_name", ""), "email": mask_email(u.get("email")), "role": u.get("role", ""),
             "level": u.get("member_level", ""), "status": u.get("status") or ("active" if u.get("is_active") else "inactive"),
             "registered_at": u.get("registered_at"), "last_login_at": u.get("last_login_at")} for u in users]
    return {"rows": rows, "form": form, "paging": paging}


