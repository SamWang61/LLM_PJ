from bson import ObjectId
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from .auth import login_required
from .db import get_db, utcnow
from .services.recommendation import recommend_products

bp = Blueprint("store", __name__)


@bp.get("/")
def home():
    db = get_db()
    category = request.args.get("category", "")
    query = {"is_active": True}
    if category:
        query["category"] = category
    products = list(db.products.find(query).sort("sales_count", -1))
    categories = db.products.distinct("category", {"is_active": True})
    recommendations = []
    if session.get("user_id"):
        events = list(db.behavior_events.find({"user_id": ObjectId(session["user_id"])}).sort("created_at", -1).limit(50))
        recommendations = recommend_products(products, events)
    return render_template("store/home.html", products=products, categories=categories,
                           selected_category=category, recommendations=recommendations)


@bp.get("/product/<product_id>")
def product_detail(product_id):
    try:
        product = get_db().products.find_one({"_id": ObjectId(product_id), "is_active": True})
    except Exception:
        abort(404)
    if not product:
        abort(404)
    if session.get("user_id"):
        get_db().behavior_events.insert_one({"user_id": ObjectId(session["user_id"]),
            "product_id": product["_id"], "event_type": "view", "created_at": utcnow()})
    return render_template("store/product.html", product=product)


@bp.post("/cart/add/<product_id>")
@login_required
def add_to_cart(product_id):
    product = get_db().products.find_one({"_id": ObjectId(product_id), "is_active": True})
    if not product:
        abort(404)
    cart = session.get("cart", {})
    cart[product_id] = min(int(cart.get(product_id, 0)) + 1, int(product.get("stock", 0)))
    session["cart"] = cart
    get_db().behavior_events.insert_one({"user_id": ObjectId(session["user_id"]),
        "product_id": product["_id"], "event_type": "cart", "created_at": utcnow()})
    flash(f"已將「{product['name']}」加入購物車。", "success")
    return redirect(request.referrer or url_for("store.home"))


@bp.get("/cart")
@login_required
def cart():
    items, total = [], 0
    for pid, qty in session.get("cart", {}).items():
        product = get_db().products.find_one({"_id": ObjectId(pid)})
        if product:
            subtotal = float(product["price"]) * qty
            items.append({"product": product, "qty": qty, "subtotal": subtotal})
            total += subtotal
    return render_template("store/cart.html", items=items, total=total)


@bp.post("/checkout")
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("購物車目前是空的。", "warning")
        return redirect(url_for("store.cart"))
    db, order_items, total = get_db(), [], 0
    for pid, qty in cart.items():
        product = db.products.find_one({"_id": ObjectId(pid), "stock": {"$gte": qty}})
        if not product:
            flash("部分商品庫存不足，請重新確認。", "danger")
            return redirect(url_for("store.cart"))
        subtotal = float(product["price"]) * qty
        order_items.append({"product_id": product["_id"], "name": product["name"],
                            "price": product["price"], "quantity": qty, "subtotal": subtotal})
        total += subtotal
    order = {"order_no": f"MC{utcnow():%Y%m%d%H%M%S}", "user_id": ObjectId(session["user_id"]),
             "items": order_items, "total": total, "status": "paid", "created_at": utcnow(), "updated_at": utcnow()}
    db.orders.insert_one(order)
    for item in order_items:
        db.products.update_one({"_id": item["product_id"]}, {"$inc": {"stock": -item["quantity"], "sales_count": item["quantity"]}})
        db.behavior_events.insert_one({"user_id": ObjectId(session["user_id"]), "product_id": item["product_id"],
                                      "event_type": "purchase", "created_at": utcnow()})
    session["cart"] = {}
    flash(f"訂單 {order['order_no']} 已成立，感謝您的購買。", "success")
    return redirect(url_for("store.home"))

