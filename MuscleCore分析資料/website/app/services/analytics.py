def build_insights(orders, products):
    revenue = sum(float(o.get("total", 0)) for o in orders if o.get("status") != "cancelled")
    paid_orders = [o for o in orders if o.get("status") != "cancelled"]
    avg_order = revenue / len(paid_orders) if paid_orders else None
    low_stock = [p for p in products if int(p.get("stock", 0)) <= int(p.get("low_stock_threshold", 5))]
    best = sorted(products, key=lambda p: p.get("sales_count", 0), reverse=True)[:3]
    messages = []
    if low_stock:
        messages.append(f"{len(low_stock)} 項商品已達補貨門檻，建議優先處理庫存風險。")
    if best:
        messages.append(f"{best[0]['name']} 為目前銷售領先商品，可搭配關聯商品提高客單價。")
    if not messages:
        messages.append("目前營運資料不足，完成更多訂單後將產生具體洞察。")
    return {"revenue": revenue, "orders": len(paid_orders), "avg_order": avg_order,
            "low_stock": low_stock, "best": best, "messages": messages}

