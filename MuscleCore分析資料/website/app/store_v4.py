"""Opt-in v4 routes; endpoint names preserve the existing storefront navigation."""
from decimal import Decimal
from functools import wraps
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo.errors import PyMongoError
from .auth import login_required, current_member
from .services.member_events import record_read_event
from .db import get_db
from .services.sku_gateway import cart_service, review_service, catalog, product_view, money, oid, CartError, CartConflict
from .services.behavior_scope import personalization_behavior_query
from .services.ai_workflows import storefront_recommendations
from .services.recommendation import policy_weights
from .services.storefront_ranking import recommendations_6_4
from .services import recommendation_logs as rec_logs

bp = Blueprint("store", __name__)


@bp.after_request
def fresh_storefront(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def recommendation_blocks(products, member, query=""):
    db = get_db()
    events = [] if not member else list(db.behavior_events.find(
        personalization_behavior_query({'user_id': member['_id']})).sort('event_at', -1).limit(1000))
    policy = db.system_configs.find_one({'config_key': 'recommendation_policy', 'status': 'active'})
    rules = list(db.cross_category_rules.find({'status': 'active'}))
    settings = (policy or {}).get('settings')
    settings = dict(settings) if isinstance(settings, dict) else {}
    settings['weights'] = policy_weights(db)
    signals = storefront_recommendations(products, events, query, weights=settings['weights'], limit=max(1, len(products)))
    semantics = {str(item['product']['_id']): item['score'] for item in signals['items']} if signals['source'] == 'bge' else {}
    result = recommendations_6_4(products, events, rules, settings, semantic_scores=semantics)
    if semantics:
        result['source'] = 'bge+rules-6plus4-rating-v1'
    return result


def attribution(action, *args):
    """Recommendation logging is best-effort: a logging failure must never break browsing or the cart."""
    try:
        return action(get_db(), *args)
    except PyMongoError:
        current_app.logger.warning("recommendation log write skipped (%s)", action.__name__)
        return None


def reviewable_lines(db, member, product_id):
    if not member or current_app.config.get('CLOUD_PREVIEW_READ_ONLY'):
        return []
    orders = {o['_id']: o for o in db.orders.find({'user_id': member['_id'], 'payment_status': 'paid',
        'status': {'$ne': 'cancelled'}, '$or': [{'status': 'completed'}, {'shipping_status': 'delivered'}]})}
    reviewed = [r['order_item_id'] for r in db.product_reviews.find({'user_id': member['_id'], 'product_id': product_id})]
    lines = db.order_items.find({'user_id': member['_id'], 'product_id': product_id,
        'order_id': {'$in': list(orders)}, '_id': {'$nin': reviewed}})
    return [{**line, 'review_order_number': orders[line['order_id']].get('order_number',
             '尾碼' + str(line['order_id'])[-6:])} for line in lines]


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
    query = request.args.get("q", "")[:200].strip()
    if member:
        if query:
            record_read_event(member, "SEARCH", query=query)
    result = recommendation_blocks(products, member, query)
    recommendation_ids = attribution(rec_logs.log_impressions, member, result) or {}
    return render_template("store/home.html", recommendation_ids=recommendation_ids, products=shown[(page-1)*24:page*24], categories=categories,
                           selected_category=category, major_categories=major_categories, selected_major=major,
                           page=page, pages=pages, total=total,
                           recommendations=result['personalized'], cross_recommendations=result['cross_category'],
                           recommendation_source=result['source'])


@bp.get('/recommendations')
@handled
def recommendations_fragment():
    member = current_member()
    result = recommendation_blocks(catalog(get_db()), member, request.args.get('q', '')[:200].strip())
    recommendation_ids = attribution(rec_logs.log_impressions, member, result) or {}
    return render_template('store/recommendations_v4.html', recommendations=result['personalized'],
                           recommendation_ids=recommendation_ids,
                           cross_recommendations=result['cross_category'])


@bp.get("/product/<product_id>")
@handled
def product_detail(product_id):
    member = current_member()
    db = get_db()
    product = db.products.find_one({"_id": oid(product_id), "schema_version": 4, "status": "active"})
    if not product:
        abort(404)
    skus = list(db.product_skus.find({"product_id": product["_id"], "status": "active"}))
    rec_id = request.args.get("rec") if attribution(rec_logs.record_click, member, request.args.get("rec"), product["_id"]) else None
    if member:
        record_read_event(member, "PRODUCT_VIEW", product=product, recommendation_id=rec_id)
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
    return render_template("store/product.html", product=product_view(product, skus, categories), rec_id=rec_id,
                           reviewable_items=reviewable_lines(db, member, product['_id']),
                           product_navigation={"previous_url": previous_url, "next_url": next_url,
                               "list_url": url_for("store.home", page=index // 24 + 1 if index is not None else 1,
                                                   _anchor="products", **context)})


@bp.post('/reviews/<order_item_id>')
@login_required
def submit_review(order_item_id):
    if current_app.config.get('CLOUD_PREVIEW_READ_ONLY'):
        return {'error': '展示環境僅供瀏覽。'}, 403
    try:
        data = payload()
        review = review_service().create_review(session['user_id'], oid(order_item_id), integer(data, 'rating'),
            title=data.get('title', ''), content=data.get('content', ''))
        product = get_db().products.find_one({'_id': review['product_id']})
        if request.is_json:
            return jsonify(review_id=str(review['_id']), product_id=str(review['product_id']),
                rating=product['average_rating_display'], rating_count=product['rating_count'],
                rating_status=product['rating_status'])
        flash('評價已送出，商品星等已更新。', 'success')
        return redirect(url_for('store.product_detail', product_id=review['product_id']), code=303)
    except CartConflict:
        return {'error': '此訂單明細已評價，不能改送其他星等或內容。'}, 409
    except CartError:
        return {'error': '請確認為本人已付款且完成或送達的訂單明細，星等須為1～5的整數。'}, 400
    except PyMongoError:
        current_app.logger.warning('Review database operation unavailable')
        return {'error': '評價暫時無法確認，請保留相同星等與內容重試。'}, 503


@bp.post("/cart/add/<product_id>")
@login_required
@handled
def add_to_cart(product_id):
    data = payload()
    sid = oid(data.get("sku_id"))
    if not get_db().product_skus.find_one({"_id": sid, "product_id": oid(product_id), "status": "active"}):
        abort(404)
    document = cart_service().add_item(session["user_id"], sid, integer(data, "quantity", 1),
                                       operation_id=data.get("operation_id"), expected_revision=revision(data))
    attribution(rec_logs.record_add_to_cart, current_member(), data.get("rec"), oid(product_id))
    return reply(document)


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
    attribution(rec_logs.record_order_purchases, current_member(), order)
    if not request.is_json:
        flash(f"示範訂單 {order['order_number']} 已建立（未串接付款）。", "success")
    return reply(order, "store.home")
