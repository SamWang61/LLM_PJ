from flask import Blueprint, render_template

from .auth import admin_required
from .db import get_db
from .services.analytics import build_insights

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@admin_required
def dashboard():
    db = get_db()
    orders = list(db.orders.find().sort("created_at", -1).limit(100))
    products = list(db.products.find({"is_active": True}))
    insights = build_insights(orders, products)
    return render_template("admin/dashboard.html", insights=insights, recent_orders=orders[:6])


@bp.get("/recommendations")
@admin_required
def recommendations():
    db = get_db()
    stats = list(db.behavior_events.aggregate([
        {"$group": {"_id": {"product_id": "$product_id", "event_type": "$event_type"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 20}
    ]))
    return render_template("admin/recommendations.html", stats=stats)

