from flask import Blueprint, current_app, render_template

from .auth import admin_required
from .db import get_db
from .services.analytics import build_insights
from .services.ai_workflows import operational_summary

bp = Blueprint("admin", __name__, url_prefix="/admin")


def dashboard_data():
    db = get_db()
    orders = list(db.orders.find().sort("created_at", -1).limit(100))
    if current_app.config["DATA_MODE"] == "v4":
        from .services.sku_gateway import money
        from decimal import Decimal
        paid = [o for o in orders if o.get("payment_status") == "paid" and o["status"] != "cancelled"]
        revenue = sum((money(o["total_amount"]) for o in paid), Decimal("0"))
        skus = list(db.product_skus.find({"status": "active", "$expr": {"$lte": ["$available_quantity", "$safety_stock"]}}))
        best = list(db.order_items.aggregate([
            {"$match": {"order_id": {"$in": [o["_id"] for o in paid]}}},
            {"$group": {"_id": "$product_id", "name": {"$first": "$product_name_snapshot"}, "sales_count": {"$sum": "$quantity"}}},
            {"$sort": {"sales_count": -1}}, {"$limit": 3}]))
        insights = {"revenue": revenue, "orders": len(paid), "avg_order": revenue / len(paid) if paid else Decimal("0"),
                    "low_stock": skus, "best": best,
                    "messages": [f"最近 100 筆訂單中有 {len(paid)} 筆有效已付款訂單（包含示範訂單）。",
                                 f"目前有 {len(skus)} 個 SKU 達補貨門檻。"]}
        return insights, [{**o, "order_no": o["order_number"], "total": money(o["total_amount"])} for o in orders[:6]]
    products = list(db.products.find({"is_active": True}))
    insights = build_insights(orders, products)
    return insights, orders[:6]


@bp.get("/")
@admin_required
def dashboard():
    insights, orders = dashboard_data()
    return render_template("admin/dashboard.html", insights=insights, recent_orders=orders, summary_source="rules")


@bp.post("/summary")
@admin_required
def summary():
    insights, orders = dashboard_data()
    result = operational_summary(insights)
    insights["messages"] = result["messages"]
    return render_template("admin/dashboard.html", insights=insights, recent_orders=orders, summary_source=result["source"])


@bp.get("/recommendations")
@admin_required
def recommendations():
    db = get_db()
    stats = list(db.behavior_events.aggregate([
        {"$group": {"_id": {"product_id": "$product_id", "event_type": "$event_type"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 20}
    ]))
    return render_template("admin/recommendations.html", stats=stats)
