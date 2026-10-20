"""Bridge the existing Flask app to the shared transactional v4 service."""
from decimal import Decimal
from pathlib import Path
import sys

# This application lives two directories below the monorepo root.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from VibeCart_AI.services.sku_cart_service import CartService
from VibeCart_AI.services.review_service import ReviewService
from VibeCart_AI.services.cart_service import CartError, CartConflict, oid as parse_oid
from bson import ObjectId
from flask import current_app, session
from ..db import get_db
from .member_events import behavior_metadata


def _member_service(factory):
    from ..auth import current_member
    from .member_sessions import token_digest, fingerprint, demo_expiration
    user = current_member()
    guard = {'session_id': None} if not user else {
        'session_id': token_digest(session.get('member_session')),
        'auth_fingerprint': fingerprint(user), 'password_hash': user.get('password_hash'),
        'role': user['role'], 'demo_expires_at': demo_expiration(user)}
    return factory(get_db(), enable_checkout=current_app.config["ENABLE_CHECKOUT"],
                   behavior_metadata=behavior_metadata(), authorization_guard=guard)


def cart_service():
    return _member_service(current_app.config.get("CART_SERVICE_FACTORY", CartService))


def review_service():
    return _member_service(current_app.config.get("REVIEW_SERVICE_FACTORY", ReviewService))


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
    source = product.get("description", "").split("商品來源：")[-1].strip()
    source_url = source if source.startswith("https://online.uni-prosperity.com.tw/zh/") else None
    return {**product, "name": product["product_name"],
            "source_url": source_url,
            "display_description": product.get("summary") or product.get("description", ""),
            "major_category": categories.get(product["major_category_id"], product["category_path"][0]),
            "category": categories.get(product["minor_category_id"], product["category_path"][-1]),
            "price": min((money(s["price"]) for s in available), default=Decimal("0")),
            "stock": sum(s["available_quantity"] for s in available),
            "rating": product["average_rating_display"], "sales_count": 0,
            "sku": product["product_code"], "skus": available}


def catalog(db):
    # Classroom catalog is paginated at the route, never silently truncated at 200.
    products = list(db.products.find({"schema_version": 4, "status": "active"}).sort("_id", 1))
    ids = [p["_id"] for p in products]
    skus = list(db.product_skus.find({"product_id": {"$in": ids}, "status": "active"}))
    categories = {c["_id"]: c["name"] for c in db.categories.find({"status": "active"})}
    by_product = {}
    for sku in skus:
        by_product.setdefault(sku["product_id"], []).append(sku)
    return [product_view(p, by_product.get(p["_id"], []), categories) for p in products]
