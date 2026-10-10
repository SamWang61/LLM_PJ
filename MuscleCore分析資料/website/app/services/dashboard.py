"""Bounded dashboard queries with Taipei calendar-date filters."""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from .analytics import build_insights
from .sku_gateway import money
from .behavior_scope import production_behavior_query

TAIPEI = timezone(timedelta(hours=8))
MAX_RANGE_ORDERS = 5000


class DashboardFilterError(ValueError):
    pass


def dashboard_filters(values):
    start, end = values.get("start", ""), values.get("end", "")
    demo = values.get("demo", "all")
    if demo not in {"all", "exclude", "only"}:
        raise DashboardFilterError("示範訂單篩選值無效。")
    result = {"start": start, "end": end, "demo": demo}
    if bool(start) != bool(end):
        raise DashboardFilterError("請同時填寫開始與結束日期。")
    if start:
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if first.isoformat() != start or last.isoformat() != end or last < first or (last - first).days > 365:
                raise ValueError()
            result["after"] = datetime.combine(first, time.min, TAIPEI).astimezone(timezone.utc)
            result["before"] = datetime.combine(last + timedelta(days=1), time.min, TAIPEI).astimezone(timezone.utc)
        except (ValueError, OverflowError):
            raise DashboardFilterError("日期需為 YYYY-MM-DD，順序正確且範圍不超過 366 天。") from None
    return result


def dated_query(filters, field):
    if "after" not in filters:
        return {}
    bounds = {"$gte": filters["after"], "$lt": filters["before"]}
    if field == "ordered_at":
        return {"$or": [{field: bounds}, {field: {"$exists": False}, "created_at": bounds}]}
    return {field: bounds}


def load_dashboard(db, mode, filters):
    field = "ordered_at" if mode == "v4" else "created_at"
    query = dated_query(filters, field)
    if mode == "v4" and filters["demo"] != "all":
        query["is_demo"] = True if filters["demo"] == "only" else {"$ne": True}
    elif mode != "v4" and filters["demo"] != "all":
        raise DashboardFilterError("舊版資料不支援示範訂單篩選。")
    limit = MAX_RANGE_ORDERS if "after" in filters else 100
    orders = list(db.orders.find(query).sort([(field, -1), ("_id", -1)]).limit(limit + 1))
    if "after" in filters and len(orders) > limit:
        raise DashboardFilterError("區間超過 5,000 筆訂單，請縮小日期範圍；未顯示截斷統計。")
    orders = orders[:limit]
    if mode == "v4":
        paid = [o for o in orders if o.get("payment_status") == "paid" and o.get("status") != "cancelled"]
        revenue = sum((money(o["total_amount"]) for o in paid), Decimal("0"))
        stock_query = {"status": "active", "$expr": {"$lte": ["$available_quantity", "$safety_stock"]}}
        stock_count = db.product_skus.count_documents(stock_query)
        low_stock = list(db.product_skus.find(stock_query).sort([("available_quantity", 1), ("sku_code", 1)]).limit(100))
        best = list(db.order_items.aggregate([
            {"$match": {"order_id": {"$in": [o["_id"] for o in paid]}}},
            {"$group": {"_id": "$product_id", "name": {"$first": "$product_name_snapshot"}, "sales_count": {"$sum": "$quantity"}}},
            {"$sort": {"sales_count": -1, "_id": 1}}, {"$limit": 10}]))
        insights = {"revenue": revenue, "orders": len(paid),
                    "avg_order": (revenue / len(paid)).quantize(Decimal("0.01")) if paid else Decimal("0"),
                    "low_stock": low_stock, "low_stock_count": stock_count, "best": best}
        recent = [{**o, "order_no": o["order_number"], "total": money(o["total_amount"])} for o in orders[:10]]
    else:
        insights = build_insights(orders, list(db.products.find({"is_active": True})))
        insights["low_stock_count"] = len(insights["low_stock"])
        paid = [o for o in orders if o.get("status") != "cancelled"]
        recent = orders[:10]
    scope = f"{filters['start']} ～ {filters['end']}（台北時間）" if "after" in filters else "最近 100 筆訂單"
    demo_label = {"all": "包含示範訂單", "exclude": "排除示範訂單", "only": "僅示範訂單"}[filters["demo"]]
    insights.update(scope=scope, scope_key="date_range" if "after" in filters else "latest_100_orders",
                    start=filters["start"], end=filters["end"], demo=filters["demo"], sampled_orders=len(orders), mode=mode,
                    messages=[f"{scope}，共 {len(orders)} 筆訂單，計入 {insights['orders']} 筆有效訂單。",
                              f"{demo_label}；目前 {insights['low_stock_count']} 個品項達補貨門檻。",
                              "v4 營收排除未付款、退款與取消訂單。" if mode == "v4" else "舊版統計依未取消訂單計算，並非付款確認報表。"])
    daily = defaultdict(lambda: {"orders": 0, "revenue": Decimal("0")})
    for order in paid:
        when = order.get("ordered_at", order.get("created_at"))
        if isinstance(when, datetime):
            key = when.replace(tzinfo=when.tzinfo or timezone.utc).astimezone(TAIPEI).date().isoformat()
            daily[key]["orders"] += 1
            daily[key]["revenue"] += money(order["total_amount"]) if mode == "v4" else Decimal(str(order.get("total", 0)))
    insights["daily"] = [{"date": key, **value} for key, value in sorted(daily.items())]
    insights["undated_orders"] = len(paid) - sum(v["orders"] for v in daily.values())
    return insights, recent


def recommendation_monitor(db, mode):
    field = "event_at" if mode == "v4" else "created_at"
    events = list(db.behavior_events.find(production_behavior_query(), {"product_id": 1, "event_type": 1}).sort([(field, -1), ("_id", -1)]).limit(1000))
    counts = Counter((str(e.get("product_id") or "—"), e.get("event_type", "UNKNOWN")) for e in events)
    stats = [{"product_id": key[0], "event_type": key[1], "count": count} for key, count in counts.most_common(20)]
    policy = db.system_configs.find_one({"config_key": "recommendation_policy", "status": "active"}) if mode == "v4" else None
    return {"stats": stats, "event_count": len(events), "policy": (policy or {}).get("settings", {})}
