"""Opt-in v4 routes; endpoint names preserve the existing storefront navigation."""
from decimal import Decimal
from functools import wraps
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo.errors import PyMongoError
from .auth import login_required, current_member
from .services.member_events import record_read_event
from .db import get_db
from .services.sku_gateway import cart_service, catalog, product_view, money, oid, CartError, CartConflict
from .services.ai_workflows import storefront_recommendations
from .services.behavior_scope import production_behavior_query

bp = Blueprint("store", __name__)


def browsing_context():
    return {"major": request.args.get("major", ""),
            "category": request.args.get("category", ""),
            "q": request.args.get("q", "")[:200].strip()}


def filtered_products(products, context):
    return [p for p in products
            if (not context["major"] or p["major_category"] == context["major"])
            and (not context["category"] or p["category"] == context["category"])
            and (not context["q"] or context["q"].casefold() in " ".join(
                [p["name"], p.get("summary", ""),
                 *[" ".join(s.get("variant_attributes", {}).values()) for s in p["skus"]]]).casefold())]


def handled(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except CartConflict:
            return {"error": "購物車已變更或操作識別碼重複，請重新確認。"}, 409
        except CartError:
            return {"error": "請檢查會員狀態、SKU、數量與操作識別碼。"}, 400
        except PyMongoError:
            current_app.logger.warning("v4 database operation unavailable")
            return {"error": "服務暫時無法使用；重試時請保留原操作識別碼。"}, 503
    return wrapped


def payload():
    data = request.get_json(silent=True) if request.is_json else request.form
    if data is None or not hasattr(data, "get"):
        raise CartError("Object payload required")
    return data


def integer(data, name, default=None):
    value = data.get(name, default)
    if request.is_json:
        if type(value) is not int:
            raise CartError("Integer required")
        return value
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise CartError("Integer required")
    try:
        return int(value)
    except (ValueError, TypeError):
        raise CartError("Integer required") from None


def reply(document, target="store.cart"):
    if request.is_json:
        return jsonify(id=str(document["_id"]), revision=document.get("revision"), status=document["status"])
    return redirect(url_for(target), code=303)


def revision(data):
    return integer(data, "expected_revision") if "expected_revision" in data else None


@bp.get("/")
@handled
def home():
    member = current_member()
    products = catalog(get_db())
    category = request.args.get("category", "")
    major = request.args.get("major", "")
    major_categories = sorted({p["major_category"] for p in products})
    major_products = [p for p in products if not major or p["major_category"] == major]
    categories = sorted({p["category"] for p in major_products})
    context = browsing_context()
    query = context["q"]
    shown = filtered_products(products, context)
    total = len(shown)
    pages = max(1, (total + 23) // 24)
    page = min(pages, max(1, request.args.get("page", 1, type=int)))
    events = []
    query = request.args.get("q", "")[:200].strip()
    if member:
        if query:
            record_read_event(member, "SEARCH", query=query)
        events = list(get_db().behavior_events.find(production_behavior_query({"user_id": member["_id"]})).sort("event_at", -1).limit(50))
    result = storefront_recommendations(shown, events, query)
    return render_template("store/home.html", products=shown[(page-1)*24:page*24], categories=categories,
                           selected_category=category, major_categories=major_categories, selected_major=major,
                           page=page, pages=pages, total=total,
                           recommendations=result["items"], recommendation_source=result["source"])


@bp.get("/product/<product_id>")
@handled
def product_detail(product_id):
    member = current_member()
    db = get_db()
    product = db.products.find_one({"_id": oid(product_id), "schema_version": 4, "status": "active"})
    if not product:
        abort(404)
    skus = list(db.product_skus.find({"product_id": product["_id"], "status": "active"}))
    if member:
        record_read_event(member, "PRODUCT_VIEW", product=product)
    categories = {c["_id"]: c["name"] for c in db.categories.find({"_id": {"$in": [product["major_category_id"], product["minor_category_id"]]}})}
    context = browsing_context()
    shown = filtered_products(catalog(db), context)
    index = next((i for i, p in enumerate(shown) if p["_id"] == product["_id"]), None)
    previous_url = next_url = None
    if index is not None:
        if index > 0:
            previous_url = url_for("store.product_detail", product_id=shown[index - 1]["_id"], **context)
        if index + 1 < len(shown):
            next_url = url_for("store.product_detail", product_id=shown[index + 1]["_id"], **context)
    return render_template("store/product.html", product=product_view(product, skus, categories),
                           product_navigation={"previous_url": previous_url, "next_url": next_url,
                               "list_url": url_for("store.home", page=index // 24 + 1 if index is not None else 1,
                                                   _anchor="products", **context)})


@bp.post("/cart/add/<product_id>")
@login_required
@handled
def add_to_cart(product_id):
    data = payload()
    sid = oid(data.get("sku_id"))
    if not get_db().product_skus.find_one({"_id": sid, "product_id": oid(product_id), "status": "active"}):
        abort(404)
    return reply(cart_service().add_item(session["user_id"], sid, integer(data, "quantity", 1),
                                         operation_id=data.get("operation_id"), expected_revision=revision(data)))


@bp.post("/cart/update/<sku_id>")
@login_required
@handled
def update_cart(sku_id):
    data = payload()
    return reply(cart_service().update_quantity(session["user_id"], sku_id, integer(data, "quantity"),
                                                operation_id=data.get("operation_id"), expected_revision=revision(data)))


@bp.post("/cart/remove/<sku_id>")
@login_required
@handled
def remove_from_cart(sku_id):
    data = payload()
    return reply(cart_service().remove_item(session["user_id"], sku_id,
        operation_id=data.get("operation_id"), expected_revision=revision(data)))


@bp.get("/cart")
@login_required
@handled
def cart():
    active = cart_service().get_active_cart(session["user_id"])
    items, total = [], Decimal("0")
    for item in (active or {}).get("items", []):
        product = get_db().products.find_one({"_id": item["product_id"]})
        subtotal = money(item["price_snapshot"]) * item["quantity"]
        items.append({"product": {"name": product["product_name"] if product else "已下架商品"},
                      "sku_id": str(item["sku_id"]), "qty": item["quantity"], "subtotal": subtotal})
        total += subtotal
    return render_template("store/cart_v4.html", items=items, total=total, cart=active,
                           checkout_enabled=current_app.config["ENABLE_CHECKOUT"])


@bp.post("/checkout")
@login_required
@handled
def checkout():
    if not current_app.config["ENABLE_CHECKOUT"]:
        return {"error": "示範結帳尚未啟用。"}, 403
    data = payload()
    order = cart_service().checkout_cart(session["user_id"], checkout_id=data.get("checkout_id"),
        cart_id=oid(data.get("cart_id")), expected_revision=integer(data, "expected_revision"))
    if not request.is_json:
        flash(f"示範訂單 {order['order_number']} 已建立（未串接付款）。", "success")
    return reply(order, "store.home")
