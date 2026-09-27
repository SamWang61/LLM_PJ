from app.services.analytics import build_insights
from app.services.recommendation import recommend_products


def test_analytics_summary():
    data = build_insights([{"total": 1000, "status": "paid"}],
                          [{"name": "啞鈴", "stock": 2, "low_stock_threshold": 5, "sales_count": 9}])
    assert data["revenue"] == 1000
    assert len(data["low_stock"]) == 1


def test_recommender_prioritizes_category():
    products = [{"_id": "1", "name": "A", "category": "重訓", "rating": 4, "sales_count": 0},
                {"_id": "2", "name": "B", "category": "瑜珈", "rating": 5, "sales_count": 0}]
    events = [{"product_id": "1", "event_type": "purchase"}]
    result = recommend_products(products, events)
    assert result[0]["product"]["name"] == "A"

