"""Check private Cloud Run D4 consumers using disposable acceptance-db rows.

Read one JSON object from stdin containing mongo_uri, id_token, service_url,
revision, and image. Secrets are never written to disk or printed.
"""

import json
import re
import secrets
import sys
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
    response = session.get(url, timeout=30)
    require(response.status_code == 200, f"HTTP {response.status_code} for {urlparse(url).path}")
    return BeautifulSoup(response.text, "html.parser")


def login(base, token, email, password):
    session = requests.Session()
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
        if heading and heading.get_text(strip=True) == "為你精選":
            cards = []
            for card in section.select("article.product-card"):
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


def verify_scope(config):
    mongo = urlparse(config["mongo_uri"])
    require(mongo.scheme == "mongodb+srv" and mongo.hostname == MONGO_HOST
            and mongo.path == "/" + DATABASE and mongo.username == MONGO_USER,
            "Mongo acceptance scope mismatch")
    service = urlparse(config["service_url"])
    require(service.scheme == "https" and service.hostname
            and service.hostname.startswith(SERVICE_PREFIX)
            and service.hostname.endswith(".a.run.app")
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


def cleanup_probe(db, marker, user_ids, sku_ids, product_ids):
    scopes = (
        ("events", db.behavior_events, {"metadata.probe_id": marker}),
        ("sessions", db.auth_sessions, {"user_id": {"$in": user_ids}}),
        ("users", db.users, {"_id": {"$in": user_ids}, "acceptance_run": marker}),
        ("skus", db.product_skus, {"_id": {"$in": sku_ids}, "acceptance_run": marker}),
        ("products", db.products, {"_id": {"$in": product_ids}, "acceptance_run": marker}),
    )
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
    emails = [f"{marker}-{role}@example.invalid" for role in ("admin", "customer")]
    password = secrets.token_urlsafe(24)
    report = {"probe_id": marker, "service_revision": config["revision"],
              "service_image": config["image"]}
    failed = None
    try:
        # Reuse only the category IDs from the existing isolated fixture.
        fixture = db.products.find_one({"schema_version": 4, "status": "active"},
                                       {"major_category_id": 1, "minor_category_id": 1,
                                        "category_path": 1})
        require(fixture and len(fixture.get("category_path", [])) >= 2,
                "Acceptance categories unavailable")
        products = [{"_id": product_ids[i], "schema_version": 4,
                     "product_code": f"{marker}-{i}",
                     "product_name": f"REN D4 隔離探針商品 {i + 1}",
                     "major_category_id": fixture["major_category_id"],
                     "minor_category_id": fixture["minor_category_id"],
                     "category_path": fixture["category_path"],
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
        require(any(str(pid) in href for href, _ in baseline_cards for pid in product_ids),
                "Probe products absent from storefront")
        db.behavior_events.insert_one(make_event(user_ids[1], product_ids[0], marker, now, False))
        normal_count = monitor_count(page(admin, monitor_url))
        normal_cards = recommendations(page(member, base + "/"))
        require(normal_count == baseline_count + 1, "Normal event absent from admin monitor")
        require(normal_cards != baseline_cards, "Normal event did not change storefront")
        require(str(product_ids[0]) in normal_cards[0][0], "Normal product did not lead")

        synthetic = [make_event(user_ids[1], product_ids[1], marker,
                                now + timedelta(seconds=i + 1), True)
                     for i in range(1001)]
        db.behavior_events.insert_many(synthetic, ordered=False)
        synthetic_count = monitor_count(page(admin, monitor_url))
        synthetic_cards = recommendations(page(member, base + "/"))
        require(synthetic_count == normal_count, "Synthetic events leaked into admin monitor")
        require(synthetic_cards == normal_cards, "Synthetic events changed storefront")
        report.update(status="passed", baseline_admin_count=baseline_count,
                      after_normal_admin_count=normal_count,
                      after_synthetic_admin_count=synthetic_count,
                      normal_visible=True, synthetic_excluded=True,
                      normal_inserted=1, synthetic_inserted=len(synthetic),
                      product_ids=[str(pid) for pid in product_ids])
    except Exception as error:
        failed = error
        report.update(status="failed", error_type=type(error).__name__,
                      error=str(error) if isinstance(error, RuntimeError) else "Probe execution failed")
    finally:
        cleanup = cleanup_probe(db, marker, user_ids, sku_ids, product_ids)
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
