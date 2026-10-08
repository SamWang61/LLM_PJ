"""AI whitelist v1: server-side aggregates sent to the cloud LLM.

Only the shapes below leave the server. No users, emails, sessions, password hashes,
raw orders, addresses or browser-supplied numbers are ever included.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from .dashboard import TAIPEI, DashboardFilterError, dashboard_filters
from .sku_gateway import money

CONTRACT_VERSION = "ai-whitelist-v1"
MAX_PERIOD_ORDERS = 5000
MAX_PRODUCTS = 100
UNAVAILABLE_FIELDS = ["visitors", "traffic", "conversion_rate", "cost", "gross_margin", "advertising"]
ORDER_FIELDS = {"_id": 1, "ordered_at": 1, "payment_status": 1, "status": 1, "total_amount": 1, "is_demo": 1}
# Products sent per intent are ordered for that question, then truncated to MAX_PRODUCTS.
PRODUCT_SORTS = {
    "replenishment": ("available_minus_safety_asc", lambda p: (p["available_quantity"] - p["safety_stock"], -p["valid_sold_units"], p["product_id"])),
    "promotion": ("valid_sold_units_asc_available_desc", lambda p: (p["valid_sold_units"], -p["available_quantity"], p["product_id"])),
}
DEFAULT_SORT = ("valid_sold_units_desc", lambda p: (-p["valid_sold_units"], p["product_id"]))


class InsightDataError(ValueError):
    """Carries a contract error code (range_too_large, data_unavailable, invalid_range)."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def money_text(value):
    return None if value is None else str(Decimal(value).quantize(Decimal("0.01")))


def pct_change(current, base):
    if base is None or current is None or Decimal(base) == 0:
        return None
    return str(((Decimal(current) - Decimal(base)) / Decimal(base) * 100).quantize(Decimal("0.1")))


def demo_query(demo):
    return {} if demo == "all" else {"is_demo": True if demo == "only" else {"$ne": True}}


def default_end(db, demo):
    """Latest Taipei date that has an order under the same demo filter, else today."""
    latest = list(db.orders.find({**demo_query(demo), "ordered_at": {"$type": "date"}}, {"ordered_at": 1}).sort("ordered_at", -1).limit(1))
    if not latest:
        return datetime.now(TAIPEI).date()
    when = latest[0]["ordered_at"]
    return when.replace(tzinfo=when.tzinfo or timezone.utc).astimezone(TAIPEI).date()


def insight_ranges(db, values):
    """Validate the current range (1–366 Taipei days) and derive the equal-length preceding period."""
    demo = values.get("demo", "all")
    start, end = values.get("start", ""), values.get("end", "")
    if not start and not end and demo in {"all", "exclude", "only"}:
        last = default_end(db, demo)
        start, end = (last - timedelta(days=6)).isoformat(), last.isoformat()
    try:
        current = dashboard_filters({"start": start, "end": end, "demo": demo})
    except DashboardFilterError as error:
        raise InsightDataError("invalid_range", str(error)) from None
    if "after" not in current:
        raise InsightDataError("invalid_range", "請同時填寫開始與結束日期。")
    first, last = date.fromisoformat(current["start"]), date.fromisoformat(current["end"])
    days = (last - first).days + 1
    previous_last = first - timedelta(days=1)
    previous_first = previous_last - timedelta(days=days - 1)
    comparison = dashboard_filters({"start": previous_first.isoformat(), "end": previous_last.isoformat(), "demo": demo})
    return current, comparison


def period_orders(db, filters):
    query = {**demo_query(filters["demo"]), "ordered_at": {"$gte": filters["after"], "$lt": filters["before"]}}
    # Count first so an oversized range is rejected instead of silently truncated.
    if db.orders.count_documents(query) > MAX_PERIOD_ORDERS:
        raise InsightDataError("range_too_large",
                               f"{filters['start']} ～ {filters['end']} 超過 {MAX_PERIOD_ORDERS:,} 筆訂單，請縮小日期範圍。")
    return list(db.orders.find(query, ORDER_FIELDS))


def is_valid(order):
    return order.get("payment_status") == "paid" and order.get("status") != "cancelled"


def taipei_date(when):
    return when.replace(tzinfo=when.tzinfo or timezone.utc).astimezone(TAIPEI).date().isoformat()


def summarize_period(filters, orders):
    valid = [o for o in orders if is_valid(o)]
    revenue = sum((money(o["total_amount"]) for o in valid), Decimal("0"))
    first, last = date.fromisoformat(filters["start"]), date.fromisoformat(filters["end"])
    daily = {(first + timedelta(days=i)).isoformat(): {"all_orders": 0, "valid_orders": 0, "revenue": Decimal("0")}
             for i in range((last - first).days + 1)}
    for order in orders:
        row = daily[taipei_date(order["ordered_at"])]
        row["all_orders"] += 1
        if is_valid(order):
            row["valid_orders"] += 1
            row["revenue"] += money(order["total_amount"])
    totals = {"all_orders": len(orders), "valid_orders": len(valid), "revenue": money_text(revenue),
              "average_order_value": money_text(revenue / len(valid)) if valid else None}
    rows = [{"date": key, "all_orders": v["all_orders"], "valid_orders": v["valid_orders"], "revenue": money_text(v["revenue"])}
            for key, v in daily.items()]
    return totals, rows, [o["_id"] for o in valid], sum(1 for o in orders if o.get("is_demo") is True)


def product_rows(db, valid_ids, intent):
    """One row per recommendable product, using its lowest-priced sellable SKU."""
    products = {p["_id"]: p for p in db.products.find({"status": "active", "is_ai_recommendable": True}, {"product_name": 1})}
    cheapest = {}
    for sku in db.product_skus.find({"status": "active", "available_quantity": {"$gt": 0}, "product_id": {"$in": list(products)}},
                                    {"product_id": 1, "price": 1, "stock_quantity": 1, "available_quantity": 1, "safety_stock": 1}):
        price = money(sku["price"])
        best = cheapest.get(sku["product_id"])
        if best is None or (price, str(sku["_id"])) < (best[0], str(best[1]["_id"])):
            cheapest[sku["product_id"]] = (price, sku)
    sold = {row["_id"]: row["units"] for row in db.order_items.aggregate([
        {"$match": {"order_id": {"$in": valid_ids}}}, {"$group": {"_id": "$product_id", "units": {"$sum": "$quantity"}}}])} if valid_ids else {}
    rows = [{"product_id": str(pid), "name": products[pid].get("product_name", ""), "sku_id": str(sku["_id"]),
             "price": money_text(price), "stock_quantity": int(sku.get("stock_quantity", 0)),
             "available_quantity": int(sku.get("available_quantity", 0)), "safety_stock": int(sku.get("safety_stock", 0)),
             "valid_sold_units": int(sold.get(pid, 0)), "promotion_eligible": None}
            for pid, (price, sku) in cheapest.items()]
    sort_name, key = PRODUCT_SORTS.get(intent, DEFAULT_SORT)
    rows.sort(key=key)
    meta = {"sort": sort_name, "total_candidates": len(rows), "returned": min(len(rows), MAX_PRODUCTS),
            "truncated": len(rows) > MAX_PRODUCTS, "excluded_without_sellable_sku": len(products) - len(cheapest)}
    return rows[:MAX_PRODUCTS], meta


def build_insight_payload(db, mode, current, comparison, intent):
    if mode != "v4":
        raise InsightDataError("data_unavailable", "雲端洞察只支援 v4 資料。")
    current_orders, comparison_orders = period_orders(db, current), period_orders(db, comparison)
    cur_totals, cur_daily, valid_ids, cur_demo = summarize_period(current, current_orders)
    cmp_totals, cmp_daily, _, cmp_demo = summarize_period(comparison, comparison_orders)
    products, products_meta = product_rows(db, valid_ids, intent)
    warnings = []
    if not cur_totals["all_orders"]:
        warnings.append("本期沒有任何訂單。")
    if not cmp_totals["valid_orders"]:
        warnings.append("比較期沒有有效訂單，成長率為 null。")
    if cur_demo or cmp_demo:
        warnings.append(f"含示範訂單：本期 {cur_demo} 筆、比較期 {cmp_demo} 筆，數字不代表真實營運。")
    if products_meta["excluded_without_sellable_sku"]:
        warnings.append(f"{products_meta['excluded_without_sellable_sku']} 個可推薦商品沒有可售 SKU，未列入 products。")
    if products_meta["truncated"]:
        warnings.append(f"products 依 {products_meta['sort']} 排序後只列前 {MAX_PRODUCTS} 筆。")

    def period(filters):
        return {"start": filters["start"], "end": filters["end"],
                "days": (date.fromisoformat(filters["end"]) - date.fromisoformat(filters["start"])).days + 1}
    return {
        "contract_version": CONTRACT_VERSION, "timezone": "Asia/Taipei", "currency": "TWD",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {"collections": ["orders", "order_items", "products", "product_skus"], "demo_filter": current["demo"],
                   "demo_orders": {"current": cur_demo, "comparison": cmp_demo}},
        "current_range": period(current), "comparison_range": period(comparison),
        "totals": {"current": cur_totals, "comparison": cmp_totals, "change_pct": {
            "valid_orders": pct_change(cur_totals["valid_orders"], cmp_totals["valid_orders"]),
            "revenue": pct_change(cur_totals["revenue"], cmp_totals["revenue"]),
            "average_order_value": pct_change(cur_totals["average_order_value"], cmp_totals["average_order_value"])}},
        "daily": {"current": cur_daily, "comparison": cmp_daily},
        "products": products, "products_meta": products_meta,
        "unavailable": UNAVAILABLE_FIELDS, "warnings": warnings,
    }
