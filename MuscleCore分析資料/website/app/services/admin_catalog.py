"""Read-only product list for the admin (design spec 6.1). Writes wait for the D5 audit migration."""
import math
import re
from bson import ObjectId
from bson.errors import InvalidId
from .sku_gateway import money

PAGE_SIZE = 50
PRODUCT_STATUSES = ("active", "inactive", "draft")
PRODUCT_FIELDS = {"product_code": 1, "product_name": 1, "major_category_id": 1, "minor_category_id": 1, "status": 1,
                  "is_ai_recommendable": 1, "average_rating_display": 1, "rating_count": 1, "image_urls": 1}


class AdminListError(ValueError):
    pass


def page_number(values):
    try:
        page = int(values.get("page", "1") or 1)
    except ValueError:
        raise AdminListError("頁碼必須是正整數。") from None
    if page < 1:
        raise AdminListError("頁碼必須是正整數。")
    return page


def keyword_pattern(raw, limit=50):
    """Case-insensitive literal match; user text is escaped so it cannot become a regex."""
    keyword = (raw or "").strip()
    if len(keyword) > limit:
        raise AdminListError(f"關鍵字最多 {limit} 字。")
    return keyword, ({"$regex": re.escape(keyword), "$options": "i"} if keyword else None)


def pagination(total, page):
    pages = max(1, math.ceil(total / PAGE_SIZE))
    return {"total": total, "page": min(page, pages), "pages": pages, "size": PAGE_SIZE}


def product_filters(values):
    keyword, pattern = keyword_pattern(values.get("q"))
    status = values.get("status", "")
    if status and status not in PRODUCT_STATUSES:
        raise AdminListError("商品狀態篩選值無效。")
    recommendable = values.get("recommendable", "")
    if recommendable not in {"", "yes", "no"}:
        raise AdminListError("可推薦篩選值無效。")
    major = values.get("major", "")
    major_id = None
    if major:
        try:
            major_id = ObjectId(major)
        except (InvalidId, TypeError):
            raise AdminListError("大類別篩選值無效。") from None
    query = {}
    if pattern:
        query["$or"] = [{"product_name": pattern}, {"product_code": pattern}]
    if status:
        query["status"] = status
    if recommendable:
        query["is_ai_recommendable"] = recommendable == "yes"
    if major_id:
        query["major_category_id"] = major_id
    form = {"q": keyword, "status": status, "recommendable": recommendable, "major": major}
    return query, form, page_number(values)


def product_list(db, values):
    query, form, page = product_filters(values)
    paging = pagination(db.products.count_documents(query), page)
    products = list(db.products.find(query, PRODUCT_FIELDS).sort([("product_code", 1), ("_id", 1)])
                    .skip((paging["page"] - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    ids = [p["_id"] for p in products]
    skus = {}
    for sku in db.product_skus.find({"product_id": {"$in": ids}}, {"product_id": 1, "status": 1, "price": 1, "available_quantity": 1}):
        stats = skus.setdefault(sku["product_id"], {"count": 0, "available": 0, "sellable_prices": []})
        stats["count"] += 1
        if sku.get("status") == "active":
            stats["available"] += int(sku.get("available_quantity", 0))
            if sku.get("available_quantity", 0) > 0:
                stats["sellable_prices"].append(money(sku["price"]))
    category_ids = {p.get(k) for p in products for k in ("major_category_id", "minor_category_id")} - {None}
    names = {c["_id"]: c["name"] for c in db.categories.find({"_id": {"$in": list(category_ids)}}, {"name": 1})}
    rows = []
    for product in products:
        stats = skus.get(product["_id"], {"count": 0, "available": 0, "sellable_prices": []})
        images = product.get("image_urls") or []
        rows.append({"id": str(product["_id"]), "code": product.get("product_code", ""), "name": product.get("product_name", ""),
                     "category": " › ".join(dict.fromkeys(n for n in (names.get(product.get("major_category_id")),
                                                                    names.get(product.get("minor_category_id"))) if n)),
                     "sku_count": stats["count"], "available": stats["available"],
                     "min_price": min(stats["sellable_prices"]) if stats["sellable_prices"] else None,
                     "rating": product.get("average_rating_display"), "rating_count": product.get("rating_count", 0),
                     "status": product.get("status", ""), "recommendable": bool(product.get("is_ai_recommendable")),
                     "image": images[0] if images else None})
    majors = list(db.categories.find({"level": 1}, {"name": 1}).sort([("sort_order", 1), ("name", 1)]))
    return {"rows": rows, "form": form, "paging": paging,
            "majors": [{"id": str(c["_id"]), "name": c["name"]} for c in majors]}
