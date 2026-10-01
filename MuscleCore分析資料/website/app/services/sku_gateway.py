"""Bridge the existing Flask app to the shared transactional v4 service."""
from decimal import Decimal
from pathlib import Path
import sys

# This application lives two directories below the monorepo root.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from VibeCart_AI.services.sku_cart_service import CartService
from VibeCart_AI.services.cart_service import CartError, CartConflict, oid as parse_oid
from bson import ObjectId
from flask import current_app
from ..db import get_db


def cart_service():
    factory = current_app.config.get("CART_SERVICE_FACTORY", CartService)
    return factory(get_db(), enable_checkout=current_app.config["ENABLE_CHECKOUT"])


def oid(value):
    if not isinstance(value, (str, ObjectId)) or not value:
        raise CartError("ObjectId required")
    return parse_oid(value)


def money(value):
    return value.to_decimal() if hasattr(value, "to_decimal") else Decimal(str(value))


def product_view(product, skus, categories=None):
    """Presentation mapping only; never write legacy fields into v4 documents."""
    available = [s for s in skus if s["status"] == "active"]
    categories = categories or {}
    return {**product, "name": product["product_name"],
            "category": categories.get(product["minor_category_id"], product["category_path"][-1]),
            "price": min((money(s["price"]) for s in available), default=Decimal("0")),
            "stock": sum(s["available_quantity"] for s in available),
            "rating": product["average_rating_display"], "sales_count": 0,
            "sku": product["product_code"], "skus": available}


def catalog(db):
    products = list(db.products.find({"schema_version": 4, "status": "active"}).sort("_id", 1).limit(200))
    ids = [p["_id"] for p in products]
    skus = list(db.product_skus.find({"product_id": {"$in": ids}, "status": "active"}))
    categories = {c["_id"]: c["name"] for c in db.categories.find({"status": "active"})}
    return [product_view(p, [s for s in skus if s["product_id"] == p["_id"]], categories) for p in products]
