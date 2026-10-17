"""Disposable N04/N05 accounts in the private, same-image acceptance service.

Credentials arrive on stdin and stay in memory. No account is left enabled.
Operator fixture disable/revoke is not an implemented D5 admin HTTP endpoint.
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from remote_d4_consumer_probe import (
    DATABASE, page, require, verify_database_roles, verify_scope,
)


def browser(token, cookies=None):
    result = requests.Session()
    result.headers["Authorization"] = "Bearer " + token
    if cookies is not None:
        result.cookies.update(cookies)
    return result


def sign_in(session, base, email, password, *, enabled=True):
    field = page(session, base + "/auth/login").select_one('input[name="csrf_token"]')
    require(field and field.get("value"), "Login CSRF missing")
    response = session.post(base + "/auth/login", data={
        "email": email, "password": password, "csrf_token": field["value"]},
        allow_redirects=False, timeout=30)
    if enabled:
        require(response.status_code in (302, 303), "Enabled fixture login failed")
    else:
        require(response.status_code == 200 and "帳號或密碼不正確" in response.text,
                "Disabled fixture login was not rejected")


def protected(session, base, route, *, allowed):
    response = session.get(base + route, allow_redirects=False, timeout=30)
    if allowed:
        require(response.status_code == 200, "Protected fixture page unavailable")
    else:
        require(response.status_code in (302, 303)
                and urlparse(response.headers.get("Location", "")).path == "/auth/login",
                "Revoked or anonymous fixture retained access")


def disable_and_revoke(db, marker, user_ids):
    """Stop fixture login first, then retire sessions, even after partial failures."""
    query = {"_id": {"$in": user_ids}, "acceptance_run": marker}
    result = {"disabled": False, "sessions_revoked": False}
    try:
        db.users.update_many(query, {"$set": {
            "status": "inactive", "is_active": False,
            "updated_at": datetime.now(timezone.utc)}})
        result["disabled"] = db.users.count_documents({
            **query, "$or": [{"status": "active"}, {"is_active": True}]}) == 0
        result["accounts_present"] = db.users.count_documents(query)
    except Exception:
        result["disable_error"] = "write_or_readback_failed"
    try:
        result["sessions_deleted"] = db.auth_sessions.delete_many({
            "user_id": {"$in": user_ids}}).deleted_count
        result["sessions_remaining"] = db.auth_sessions.count_documents({
            "user_id": {"$in": user_ids}})
        result["sessions_revoked"] = result["sessions_remaining"] == 0
    except Exception:
        result["session_error"] = "write_or_readback_failed"
    result["verified"] = result["disabled"] and result["sessions_revoked"]
    return result


def cleanup(db, marker, user_ids):
    result = {"retirement": disable_and_revoke(db, marker, user_ids)}
    try:
        query = {"_id": {"$in": user_ids}, "acceptance_run": marker}
        result["users_deleted"] = db.users.delete_many(query).deleted_count
        result["users_remaining"] = db.users.count_documents(query)
    except Exception:
        result["users_remaining"] = "write_or_readback_failed"
    result["verified"] = result["retirement"]["verified"] and result["users_remaining"] == 0
    return result


def run(config):
    verify_scope(config)  # Reject production URLs/URIs before opening any connection.
    client = MongoClient(config["mongo_uri"], serverSelectionTimeoutMS=15000)
    db = client[DATABASE]
    marker = "sam-accounts-" + secrets.token_hex(8)
    ids = {role: ObjectId() for role in ("admin", "customer")}
    credentials = {role: (marker + "-" + role + "@example.invalid", secrets.token_urlsafe(24))
                   for role in ids}
    report = {"probe_id": marker, "database": DATABASE,
              "service_revision": config["revision"], "service_image": config["image"],
              "accounts": [{"role": role, "id": str(uid)} for role, uid in ids.items()],
              "status": "failed", "checks": {}, "credentials_persisted": False}
    scope_verified = False
    try:
        db.command("ping")
        verify_database_roles(client)
        scope_verified = True
        now = datetime.now(timezone.utc)
        for role, uid in ids.items():
            email, password = credentials[role]
            db.users.insert_one({"_id": uid, "schema_version": 4, "role": role,
                "status": "active", "is_active": True, "email": email,
                "display_name": "SAM controlled " + role,
                "password_hash": generate_password_hash(password),
                "acceptance_run": marker, "created_at": now, "updated_at": now})
        base, token = config["service_url"].rstrip("/"), config["id_token"]
        anon = browser(token)
        for route in ("/cart", "/admin/"):
            protected(anon, base, route, allowed=False)
        report["checks"]["anonymous_member_admin_denied"] = True

        admin, first, second = (browser(token) for _ in range(3))
        sign_in(admin, base, *credentials["admin"])
        for route in ("/admin/", "/admin/recommendations"):
            protected(admin, base, route, allowed=True)
        report["checks"]["admin_read_pages"] = True
        for session in (first, second):
            sign_in(session, base, *credentials["customer"])
            protected(session, base, "/cart", allowed=True)
        denied = first.get(base + "/admin/", allow_redirects=False, timeout=30)
        require(denied.status_code in (302, 303)
                and urlparse(denied.headers.get("Location", "")).path == "/",
                "Customer reached the admin page")
        require(db.auth_sessions.count_documents({"user_id": ids["customer"]}) == 2,
                "Expected two independent customer sessions")
        report["checks"]["customer_two_sessions_admin_denied"] = True

        old_cookie = first.cookies.copy()
        sign_in(first, base, *credentials["customer"])
        protected(browser(token, old_cookie), base, "/cart", allowed=False)
        for session in (first, second):
            protected(session, base, "/cart", allowed=True)
        require(db.auth_sessions.count_documents({"user_id": ids["customer"]}) == 2,
                "Relogin leaked an old session or evicted the second device")
        report["checks"]["same_browser_relogin_old_cookie_denied_second_device_live"] = True

        first_cookie, second_cookie = first.cookies.copy(), second.cookies.copy()
        retired = db.auth_sessions.delete_many({"user_id": ids["customer"]}).deleted_count
        require(retired == 2 and db.auth_sessions.count_documents({
            "user_id": ids["customer"]}) == 0, "Global session retirement readback mismatch")
        for jar in (first_cookie, second_cookie):
            protected(browser(token, jar), base, "/cart", allowed=False)
        protected(admin, base, "/admin/", allowed=True)
        report["checks"]["all_customer_sessions_revoked_admin_unaffected"] = True

        for session in (first, second):
            sign_in(session, base, *credentials["customer"])
            protected(session, base, "/cart", allowed=True)
        before_disable = [first.cookies.copy(), second.cookies.copy()]
        stopped = disable_and_revoke(db, marker, list(ids.values()))
        require(stopped["verified"] and stopped.get("accounts_present") == 2
                and stopped.get("sessions_deleted") == 3, "Fixture retirement failed")
        for jar in before_disable:
            protected(browser(token, jar), base, "/cart", allowed=False)
        protected(admin, base, "/admin/", allowed=False)
        for role, route in (("admin", "/admin/"), ("customer", "/cart")):
            rejected = browser(token)
            sign_in(rejected, base, *credentials[role], enabled=False)
            protected(rejected, base, route, allowed=False)
        report["retirement_before_cleanup"] = stopped
        report["checks"]["disabled_accounts_login_and_all_devices_denied"] = True

        db.users.update_one({"_id": ids["customer"], "acceptance_run": marker},
                            {"$set": {"status": "active", "is_active": True}})
        for jar in before_disable:
            protected(browser(token, jar), base, "/cart", allowed=False)
        renewed = browser(token)
        sign_in(renewed, base, *credentials["customer"])
        protected(renewed, base, "/cart", allowed=True)
        report["checks"]["reenable_requires_new_login_old_cookies_stay_invalid"] = True
        report["status"] = "passed"
    except Exception as error:
        report.update(error_type=type(error).__name__,
                      error=str(error) if isinstance(error, RuntimeError) else "Account probe failed")
    finally:
        # A broad/wrong credential never obtains permission to write, even in cleanup.
        if scope_verified:
            report["cleanup"] = cleanup(db, marker, list(ids.values()))
            if not report["cleanup"]["verified"]:
                report["status"] = "cleanup_failed"
        else:
            report["cleanup"] = {"verified": False, "not_started": "scope_not_verified"}
        client.close()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1)
