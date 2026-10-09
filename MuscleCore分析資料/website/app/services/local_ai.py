"""AI panel A: local BGE similar-product ranking for administrators.

Inference runs on this machine; product text never leaves the server. Candidates follow the
sellable rule: active, AI-recommendable products with at least one active SKU in stock.
"""
from datetime import datetime
from time import perf_counter
from flask import current_app
from .ai_workflows import CachedEmbeddings, bge_embeddings, cosine, product_text, record_ai_call
from .dashboard import TAIPEI
from .sku_gateway import money

TOP_K = 5
PRODUCT_FIELDS = {"product_name": 1, "product_code": 1, "major_category_id": 1, "minor_category_id": 1, "summary": 1,
                  "description": 1, "product_tags": 1, "image_urls": 1}
INSTALL_COMMANDS = [
    r".venv\Scripts\python.exe -m pip install -r requirements-ai.txt",
    ".venv\\Scripts\\python.exe -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('{model}')\"",
]


class LocalModelUnavailable(RuntimeError):
    """Raised with a reason code: not_installed (package missing) or model_missing (weights not downloaded)."""
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def sellable_products(db):
    """Products eligible for recommendation, each with its lowest sellable SKU price and category names."""
    products = {p["_id"]: p for p in db.products.find({"status": "active", "is_ai_recommendable": True}, PRODUCT_FIELDS)}
    prices = {}
    for sku in db.product_skus.find({"status": "active", "available_quantity": {"$gt": 0}, "product_id": {"$in": list(products)}},
                                    {"product_id": 1, "price": 1}):
        price = money(sku["price"])
        prices[sku["product_id"]] = min(price, prices.get(sku["product_id"], price))
    category_ids = {p.get(k) for p in products.values() for k in ("major_category_id", "minor_category_id")} - {None}
    names = {c["_id"]: c["name"] for c in db.categories.find({"_id": {"$in": list(category_ids)}}, {"name": 1})}
    rows = []
    for pid, price in prices.items():
        product = products[pid]
        major, minor = names.get(product.get("major_category_id"), ""), names.get(product.get("minor_category_id"), "")
        images = product.get("image_urls") or []
        rows.append({"id": str(pid), "name": product.get("product_name", ""), "code": product.get("product_code", ""),
                     "category": " › ".join(dict.fromkeys(n for n in (major, minor) if n)), "price": price,
                     "tags": list(product.get("product_tags") or []), "image": images[0] if images else None,
                     "text": model_text(product, major, minor)})
    rows.sort(key=lambda r: (r["category"], r["name"], r["id"]))
    return rows


def model_text(product, major, minor):
    # Category codes in category_path carry no meaning for the model; use category names instead.
    return product_text({"name": product.get("product_name", ""), "category": f"{major} {minor}".strip(),
                         "summary": product.get("summary", ""), "description": product.get("description", ""),
                         "product_tags": " ".join(product.get("product_tags") or [])})


def local_embeddings():
    """Return the cached embedding model or raise LocalModelUnavailable; never substitutes fake vectors."""
    factory = current_app.config.get("EMBEDDINGS_FACTORY")
    try:
        model = factory() if factory else bge_embeddings()
    except ImportError:
        raise LocalModelUnavailable("not_installed") from None
    except Exception:
        current_app.extensions.pop("bge_embeddings", None)
        raise LocalModelUnavailable("model_missing") from None
    if not isinstance(model, CachedEmbeddings):
        # Test factories may return a bare model; keep one cache per app so hit counts stay meaningful.
        cache = current_app.extensions.get("local_embeddings_cache")
        if cache is None or cache.delegate is not model:
            cache = current_app.extensions["local_embeddings_cache"] = CachedEmbeddings(model)
        model = cache
    return model


def embed(model, texts):
    try:
        return model.embed_documents(texts)
    except Exception:
        raise LocalModelUnavailable("model_missing") from None


def similar_products(products, base_id):
    """Rank every other sellable product by cosine similarity to the base product's text."""
    base = next((p for p in products if p["id"] == base_id), None)
    if base is None:
        raise KeyError(base_id)
    model = local_embeddings()
    texts = [p["text"] for p in products]
    hits = model.cached_count(texts)
    started = perf_counter()
    vectors = embed(model, texts)
    by_id = dict(zip((p["id"] for p in products), vectors))
    scored = sorted(((cosine(by_id[base_id], by_id[p["id"]]), p) for p in products if p["id"] != base_id),
                    key=lambda pair: (-pair[0], pair[1]["id"]))
    elapsed = round((perf_counter() - started) * 1000)
    record_ai_call({"provider": "bge", "kind": "similar_products", "model": current_app.config["BGE_MODEL"],
                    "latency_ms": elapsed, "cache_hits": hits, "total": len(texts)})
    return {"base": base, "items": [{**p, "score": round(score, 4)} for score, p in scored[:TOP_K]],
            "latency_ms": elapsed, "cache_hits": hits, "total": len(texts)}


def refresh_vectors(products):
    """Drop cached vectors and re-embed every sellable product."""
    model = local_embeddings()
    model.clear()
    started = perf_counter()
    embed(model, [p["text"] for p in products])
    elapsed = round((perf_counter() - started) * 1000)
    current_app.extensions["local_vectors_refreshed_at"] = datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M")
    record_ai_call({"provider": "bge", "kind": "refresh_vectors", "model": current_app.config["BGE_MODEL"],
                    "latency_ms": elapsed, "total": len(products)})
    return {"count": len(products), "latency_ms": elapsed}


def vector_status():
    model = current_app.extensions.get("bge_embeddings") or current_app.extensions.get("local_embeddings_cache")
    return {"cached": len(model.cache) if isinstance(model, CachedEmbeddings) else 0,
            "refreshed_at": current_app.extensions.get("local_vectors_refreshed_at")}


def install_commands():
    return [command.format(model=current_app.config["BGE_MODEL"]) for command in INSTALL_COMMANDS]
