"""Local AI (panel A): BGE similar products with fake embeddings (T3 / R09)."""
import re
import pytest
from bson import Decimal128, ObjectId
from test_v4_routes import shop


class KeywordEmbeddings:
    """Deterministic fake: vectors from keyword presence, so similarity order is predictable."""
    KEYWORDS = ("乳清", "蛋白", "瑜珈", "啞鈴")

    def __init__(self):
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        return [[1.0 if k in t else 0.0 for k in self.KEYWORDS] + [0.1] for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def add_product(db, name, price="100.00", available=5, status="active", recommendable=True, sku_status="active", **extra):
    pid = db.products.insert_one({"product_name": name, "status": status, "is_ai_recommendable": recommendable,
                                  "summary": name, "description": name, "product_tags": [], **extra}).inserted_id
    db.product_skus.insert_one({"product_id": pid, "status": sku_status, "price": Decimal128(price),
                                "available_quantity": available, "stock_quantity": available, "safety_stock": 1})
    return pid


@pytest.fixture
def local(shop):
    app, client, db, uid, pid, sid = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    model = KeywordEmbeddings()
    app.config["EMBEDDINGS_FACTORY"] = lambda: model
    major, minor = ObjectId(), ObjectId()
    db.categories.insert_many([{"_id": major, "name": "運動營養"}, {"_id": minor, "name": "高蛋白"}])
    ids = {"base": add_product(db, "乳清蛋白 巧克力", major_category_id=major, minor_category_id=minor,
                               image_urls=["https://img.example.test/whey.jpg"], product_tags=["增肌"]),
           "close": add_product(db, "乳清蛋白 香草", price="80.00"),
           "half": add_product(db, "大豆蛋白"),
           "far": add_product(db, "瑜珈墊")}
    return app, client, db, model, ids


def page(client, url, status=200):
    response = client.get(url)
    assert response.status_code == status
    return response.get_data(as_text=True)


def names_in_order(html):
    return re.findall(r'<div class="similar-info"><span>([^<]+)</span>', html)


def test_top_similar_ranked_with_scores_and_meta(local):
    _, client, _, _, ids = local
    html = page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    ranked = names_in_order(html)
    assert ranked[:2] == ["乳清蛋白 香草", "大豆蛋白"] and "瑜珈墊" in ranked and "乳清蛋白 巧克力" not in ranked
    assert 'role="meter"' in html and "1.00</strong>" in html
    assert "處理時間" in html and "快取命中 0/" in html and "BAAI/bge-small-zh-v1.5" in html
    assert "運動營養 › 高蛋白" in html and "https://img.example.test/whey.jpg" in html and "增肌" in html
    assert "模型輸入文字預覽" in html


def test_top_k_is_five(local):
    _, client, db, _, ids = local
    for n in range(6):
        add_product(db, f"蛋白棒 {n}")
    assert len(names_in_order(page(client, f"/admin/ai/recommendation?product_id={ids['base']}"))) == 5


def test_unsellable_products_excluded_and_price_uses_sellable_sku(local):
    _, client, db, _, ids = local
    add_product(db, "乳清蛋白 下架", status="inactive")
    add_product(db, "乳清蛋白 不可推薦", recommendable=False)
    add_product(db, "乳清蛋白 缺貨", available=0)
    add_product(db, "乳清蛋白 SKU停用", sku_status="inactive")
    db.product_skus.insert_one({"product_id": ids["close"], "status": "inactive", "price": Decimal128("1.00"),
                                "available_quantity": 9, "stock_quantity": 9, "safety_stock": 1})
    html = page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    for hidden in ("下架", "不可推薦", "缺貨", "SKU停用"):
        assert f"乳清蛋白 {hidden}" not in html
    assert "NT$ 80.00" in html and "NT$ 1.00" not in html


def test_ineligible_base_product_is_404(local):
    _, client, db, _, _ = local
    hidden = add_product(db, "下架商品", status="inactive")
    html = page(client, f"/admin/ai/recommendation?product_id={hidden}", status=404)
    assert "找不到這個商品" in html and 'class="similar-row"' not in html


def test_cache_hits_reported_on_second_run(local):
    _, client, _, model, ids = local
    page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    html = page(client, f"/admin/ai/recommendation?product_id={ids['close']}")
    total = re.search(r"快取命中 (\d+)/(\d+)", html)
    assert total and total.group(1) == total.group(2) and model.calls == 1


def test_missing_model_shows_install_hint_without_fake_results(local):
    app, client, _, _, ids = local
    def missing():
        raise ImportError("langchain_huggingface")
    app.config["EMBEDDINGS_FACTORY"] = missing
    html = page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    assert "本機模型套件尚未安裝" in html and "requirements-ai.txt" in html and "SentenceTransformer" in html
    assert 'class="similar-row"' not in html


def test_model_load_failure_is_reported_as_missing_weights(local):
    app, client, _, _, ids = local
    def broken():
        raise OSError("weights not found at secret/path")
    app.config["EMBEDDINGS_FACTORY"] = broken
    html = page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    assert "模型檔案尚未下載或無法載入" in html and "secret/path" not in html


def test_refresh_vectors_requires_csrf_and_reembeds(local):
    app, client, _, model, ids = local
    assert client.post("/admin/ai/recommendation/refresh", data={"product_id": str(ids["base"])}).status_code == 400
    response = client.post("/admin/ai/recommendation/refresh", data={"csrf_token": "test-csrf", "product_id": str(ids["base"])})
    assert response.status_code == 302 and f"product_id={ids['base']}" in response.location
    assert model.calls == 1
    html = page(client, response.location)
    assert "已更新 5 筆商品向量" in html and "最後更新" in html and "向量快取 5 筆" in html
    assert app.extensions["ai_calls"][-1]["provider"] == "bge"


def test_refresh_reports_missing_model(local):
    app, client, _, _, _ = local
    app.config["EMBEDDINGS_FACTORY"] = lambda: (_ for _ in ()).throw(ImportError("x"))
    response = client.post("/admin/ai/recommendation/refresh", data={"csrf_token": "test-csrf"}, follow_redirects=True)
    assert "無法更新向量：本機模型套件尚未安裝" in response.get_data(as_text=True)


def test_empty_catalog_shows_empty_state(shop):
    app, client, db, uid, _, _ = shop
    db.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    db.product_skus.delete_many({})
    html = page(client, "/admin/ai/recommendation")
    assert "資料庫尚無可推薦商品" in html and "/admin/ai/recommendation/refresh" not in html


def test_dropdown_lists_only_sellable_and_measures_calls(local):
    app, client, db, _, ids = local
    add_product(db, "下架不列", status="inactive")
    html = page(client, "/admin/ai/recommendation")
    assert "下架不列" not in html and "5 個可推薦且可購買" in html and "請先選擇一個商品" in html
    page(client, f"/admin/ai/recommendation?product_id={ids['base']}")
    entry = app.extensions["ai_calls"][-1]
    assert entry["provider"] == "bge" and entry["kind"] == "similar_products" and entry["total"] == 5


def test_local_page_requires_admin(shop):
    _, client, _, _, _, _ = shop
    assert client.get("/admin/ai/recommendation").status_code == 302
    assert client.post("/admin/ai/recommendation/refresh", data={"csrf_token": "test-csrf"}).status_code == 302
