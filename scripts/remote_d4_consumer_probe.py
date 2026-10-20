"""Check private Cloud Run D4 consumers using disposable acceptance-db rows.

Read one JSON object from stdin containing mongo_uri, id_token, service_url,
revision, and image. Secrets are never written to disk or printed.
"""

import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bson import Decimal128, ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash


DATABASE = "vibecart_acceptance_pr21"
MONGO_HOST = "vibecart-ai-free.odqe25w.mongodb.net"
MONGO_USER = "sam_pr21_acceptance_20261017"
SERVICE_PREFIX = "vibecart-acceptance-pr21-"


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def page(session, url):
    # Retry only GET transport failures. POSTs keep their operation IDs and are
    # never blindly replayed here. A repeated read may create another read event.
    for attempt in range(3):
        try:
            response = session.get(url, timeout=(10, 45))
            break
        except requests.RequestException as error:
            if attempt == 2:
                raise RuntimeError('GET ' + urlparse(url).path + ' transport failed after 3 attempts ('
                                   + type(error).__name__ + ')') from None
            session.close()  # Discard stale connections; preserve this session's cookie jar.
            time.sleep(0.5 * (attempt + 1))
    require(response.status_code == 200, f"HTTP {response.status_code} for {urlparse(url).path}")
    return BeautifulSoup(response.text, "html.parser")


def login(base, token, email, password):
    session = requests.Session()
    if os.environ.get('REN_PRIVATE_HTTP_TRANSPORT') == 'node-fetch':
        from private_https_transport import mount_private_transport
        mount_private_transport(session)
    session.headers["Authorization"] = "Bearer " + token
    csrf = page(session, base + "/auth/login").select_one('input[name="csrf_token"]')
    require(csrf and csrf.get("value"), "Login CSRF field missing")
    response = session.post(base + "/auth/login", data={
        "email": email, "password": password, "csrf_token": csrf["value"]},
        timeout=30, allow_redirects=False)
    require(response.status_code in (302, 303), f"Login HTTP {response.status_code}")
    return session


def monitor_count(soup):
    match = re.search(r"實際讀取\s*([\d,]+)\s*筆", soup.get_text(" ", strip=True))
    require(match, "Admin monitor count missing")
    return int(match.group(1).replace(",", ""))


def recommendations(soup):
    for section in soup.select("section"):
        heading = section.find("h2")
        if heading and heading.get_text(strip=True) in ("為你精選", "猜你喜歡 · 6＋4"):
            cards = []
            # The new layout has separate personal and cross-category grids.
            # Existing isolation comparisons must continue to inspect only the
            # personal result, rather than accidentally mixing both candidate sets.
            grid = section.select_one(".product-grid") if section.get("aria-label") == "猜你喜歡6加4" else section
            require(grid is not None, "Personal recommendation grid missing")
            for card in grid.select("article.product-card"):
                link, reason = card.select_one("h3 a"), card.select_one(".reason")
                if link and reason:
                    cards.append((link.get("href", ""), reason.get_text(strip=True)))
            return cards
    raise RuntimeError("Storefront recommendations missing")


def make_event(user_id, product_id, marker, when, synthetic):
    metadata = {"probe_id": marker}
    if synthetic:
        metadata.update(synthetic=True, synthetic_batch_id=marker,
                        exclude_from_attribution=True)
    return {"_id": ObjectId(), "schema_version": 4,
            "event_id": f"{marker}-{secrets.token_hex(8)}", "user_id": user_id,
            "anonymous_id": None, "session_id": marker,
            "event_type": "PRODUCT_VIEW", "product_id": product_id,
            "major_category_id": None, "minor_category_id": None,
            "quantity": 1, "order_id": None, "cart_id": None,
            "search_query": None, "source": "ren_d4_private_probe",
            "recommendation_id": None, "event_at": when, "created_at": when,
            "score_version": 1, "processed_at": None, "metadata": metadata}


def distinct_category_fixtures(products):
    """Two existing category branches make leaked synthetic preference detectable."""
    by_major = {}
    for product in products:
        if len(product.get('category_path', [])) >= 2 and product.get('major_category_id'):
            by_major.setdefault(product['major_category_id'], product)
        if len(by_major) == 2:
            return list(by_major.values())
    raise RuntimeError('Two distinct acceptance category branches required')


def leading_major_category(db, cards):
    require(cards, 'Normal preference produced no personal recommendations')
    match = re.fullmatch(r'/product/([0-9a-f]{24})', urlparse(cards[0][0]).path)
    require(match, 'Unexpected personal recommendation URL')
    product = db.products.find_one({'_id': ObjectId(match.group(1))}, {'major_category_id': 1})
    require(product and product.get('major_category_id'), 'Leading recommendation category unavailable')
    return product['major_category_id']


def isolated_category_branch(marker, category_ids, now):
    major, minor = category_ids
    major_code, minor_code = marker+'-major', marker+'-minor'
    documents = [{'_id': major, 'schema_version': 4, 'category_code': major_code,
                  'name': '隔離事件大類 '+marker, 'level': 1, 'parent_id': None,
                  'path': [major_code], 'status': 'active', 'sort_order': 0,
                  'created_at': now, 'updated_at': now},
                 {'_id': minor, 'schema_version': 4, 'category_code': minor_code,
                  'name': '隔離事件小類 '+marker, 'level': 2, 'parent_id': major,
                  'path': [major_code, minor_code], 'status': 'active', 'sort_order': 0,
                  'created_at': now, 'updated_at': now}]
    return documents, {'major_category_id': major, 'minor_category_id': minor,
                       'category_path': [major_code, minor_code]}


def verify_scope(config):
    mongo = urlparse(config["mongo_uri"])
    require(mongo.scheme == "mongodb+srv" and mongo.hostname == MONGO_HOST
            and mongo.path == "/" + DATABASE and mongo.username == MONGO_USER,
            "Mongo acceptance scope mismatch")
    service = urlparse(config["service_url"])
    tagged_host = re.fullmatch(r"[a-z][a-z0-9-]{0,20}---vibecart-acceptance-pr21-[a-z0-9-]+\.a\.run\.app",
                              service.hostname or "")
    require(service.scheme == "https" and service.hostname
            and (service.hostname.startswith(SERVICE_PREFIX) or tagged_host)
            and service.hostname.endswith(".a.run.app")
            and not service.username and not service.password and service.port in (None, 443)
            and not service.path and not service.query,
            "Private Cloud Run scope mismatch")
    require(config["revision"].startswith(SERVICE_PREFIX), "Revision scope mismatch")
    require(re.search(r"@sha256:[a-f0-9]{64}$", config["image"]), "Pinned image identity missing")


def verify_database_roles(client):
    info = client.admin.command("connectionStatus").get("authInfo", {})
    roles = info.get("authenticatedUserRoles", [])
    require(len(roles) == 1 and roles[0] == {"role": "readWrite", "db": DATABASE},
            "Mongo acceptance role scope mismatch")
    users = info.get("authenticatedUsers", [])
    require(len(users) == 1 and users[0].get("user") == MONGO_USER,
            "Mongo authenticated user mismatch")


def cleanup_probe(db, marker, user_ids, sku_ids, product_ids, category_ids=()):
    scopes = [
        ("events", db.behavior_events, {"metadata.probe_id": marker}),
        ("sessions", db.auth_sessions, {"user_id": {"$in": user_ids}}),
        ("users", db.users, {"_id": {"$in": user_ids}, "acceptance_run": marker}),
        ("skus", db.product_skus, {"_id": {"$in": sku_ids}, "acceptance_run": marker}),
        ("products", db.products, {"_id": {"$in": product_ids}, "acceptance_run": marker}),
    ]
    if category_ids:
        scopes.append(('categories', db.categories, {'_id': {'$in': category_ids},
            'category_code': {'$in': [marker+'-major', marker+'-minor']}}))
    cleanup = {}
    for name, collection, query in scopes:
        try:
            cleanup[name] = collection.delete_many(query).deleted_count
        except Exception:
            cleanup[name] = "delete_failed"
    for name, collection, query in scopes:
        try:
            cleanup[name + "_remaining"] = collection.count_documents(query)
        except Exception:
            cleanup[name + "_remaining"] = "readback_failed"
    cleanup["verified"] = all(
        isinstance(cleanup[name], int) and cleanup[name + "_remaining"] == 0
        for name, _, _ in scopes)
    return cleanup


def run(config):
    verify_scope(config)
    db_client = MongoClient(config["mongo_uri"], serverSelectionTimeoutMS=15000)
    db = db_client[DATABASE]
    db.command("ping")
    verify_database_roles(db_client)
    marker = "ren-d4-" + secrets.token_hex(8)
    base = config["service_url"].rstrip("/")
    now = datetime.now(timezone.utc)
    product_ids = [ObjectId(), ObjectId()]
    sku_ids = [ObjectId(), ObjectId()]
    user_ids = [ObjectId(), ObjectId()]
    category_ids = [ObjectId(), ObjectId()]
    emails = [f"{marker}-{role}@example.invalid" for role in ("admin", "customer")]
    password = secrets.token_urlsafe(24)
    report = {"probe_id": marker, "service_revision": config["revision"],
              "service_image": config["image"]}
    failed = None
    try:
        # Reuse only the category IDs from the existing isolated fixture.
        existing = list(db.products.find(
            {"schema_version": 4, "status": "active"},
            {"major_category_id": 1, "minor_category_id": 1, "category_path": 1}).sort('_id', 1))
        try:
            fixtures = distinct_category_fixtures(existing)
            report['temporary_category_branch_created'] = False
        except RuntimeError:
            first = next((p for p in existing if len(p.get('category_path', [])) >= 2), None)
            require(first, 'Acceptance categories unavailable')
            categories, second = isolated_category_branch(marker, category_ids, now)
            # IDs and exact unique codes are registered before the first write;
            # a partial insert is cleaned in finally without touching old categories.
            db.categories.insert_many(categories)
            fixtures = distinct_category_fixtures([first, second])
            report['temporary_category_branch_created'] = True
        products = [{"_id": product_ids[i], "schema_version": 4,
                     "product_code": f"{marker}-{i}",
                     "product_name": f"REN D4 隔離探針商品 {i + 1}",
                     "major_category_id": fixtures[i]["major_category_id"],
                     "minor_category_id": fixtures[i]["minor_category_id"],
                     "category_path": fixtures[i]["category_path"],
                     "average_rating_display": 0, "image_urls": [],
                     "summary": "僅供隔離事件驗收，測後刪除", "status": "active",
                     "is_ai_recommendable": True, "acceptance_run": marker,
                     "created_at": now} for i in range(2)]
        skus = [{"_id": sku_ids[i], "schema_version": 4,
                 "product_id": product_ids[i], "sku_code": f"{marker}-sku-{i}",
                 "variant_attributes": {}, "status": "active",
                 "price": Decimal128("10.00"), "available_quantity": 100,
                 "stock_quantity": 100, "reserved_quantity": 0,
                 "safety_stock": 0, "acceptance_run": marker,
                 "created_at": now} for i in range(2)]
        db.products.insert_many(products)
        db.product_skus.insert_many(skus)
        db.users.insert_many([{"_id": user_ids[i], "schema_version": 4,
                               "status": "active", "is_active": True,
                               "role": role, "email": emails[i],
                               "display_name": "REN D4 probe",
                               "password_hash": generate_password_hash(password),
                               "acceptance_run": marker,
                               "created_at": now, "updated_at": now}
                              for i, role in enumerate(("admin", "customer"))])

        admin = login(base, config["id_token"], emails[0], password)
        member = login(base, config["id_token"], emails[1], password)
        monitor_url = base + "/admin/recommendations"
        baseline_count = monitor_count(page(admin, monitor_url))
        baseline_cards = recommendations(page(member, base + "/"))
        # Unrated fixtures correctly need not appear in cold-start high-star
        # recommendations. Do not fabricate ratings to force that old assumption.
        db.behavior_events.insert_one(make_event(user_ids[1], product_ids[0], marker, now, False))
        normal_count = monitor_count(page(admin, monitor_url))
        normal_cards = recommendations(page(member, base + "/"))
        require(normal_count == baseline_count + 1, "Normal event absent from admin monitor")
        require(normal_cards != baseline_cards, "Normal event did not change storefront")
        require(leading_major_category(db, normal_cards) == fixtures[0]['major_category_id'],
                'Normal category did not lead personal recommendations')

        synthetic = [make_event(user_ids[1], product_ids[1], marker,
                                now + timedelta(seconds=i + 1), True)
                     for i in range(1001)]
        db.behavior_events.insert_many(synthetic, ordered=False)
        synthetic_count = monitor_count(page(admin, monitor_url))
        synthetic_cards = recommendations(page(member, base + "/"))
        require(synthetic_count == normal_count, "Synthetic events leaked into admin monitor")
        require(synthetic_cards == normal_cards, "Synthetic events changed storefront")
        require(leading_major_category(db, synthetic_cards) == fixtures[0]['major_category_id'],
                'Synthetic category displaced the normal category')
        report.update(status="passed", baseline_admin_count=baseline_count,
                      after_normal_admin_count=normal_count,
                      after_synthetic_admin_count=synthetic_count,
                      normal_visible=True, synthetic_excluded=True,
                      distinct_major_categories=True, normal_category_led=True,
                      fabricated_ratings=False,
                      normal_inserted=1, synthetic_inserted=len(synthetic),
                      product_ids=[str(pid) for pid in product_ids])
    except Exception as error:
        failed = error
        report.update(status="failed", error_type=type(error).__name__,
                      error=str(error) if isinstance(error, RuntimeError) else "Probe execution failed")
    finally:
        cleanup = cleanup_probe(db, marker, user_ids, sku_ids, product_ids, category_ids)
        report["cleanup"] = cleanup
        if not cleanup["verified"]:
            report["status"] = "cleanup_failed"
        db_client.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if failed is None and report["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        # Do not print third-party exception messages: they may contain URI credentials.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1)
