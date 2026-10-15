"""Cloud-only factory. No database seeds, accounts or migrations at startup."""
import os
from urllib.parse import urlparse

from flask import abort, request, session
from pymongo.errors import PyMongoError

from app import create_app
from app.db import get_db


def create_cloud_app():
    uri = os.environ.get("MONGO_URI", "")
    secret = os.environ.get("SECRET_KEY", "")
    if urlparse(uri).hostname != "vibecart-ai-free.odqe25w.mongodb.net":
        raise RuntimeError("MONGO_URI must target the authorized VibeCart cluster")
    if len(secret) < 32 or secret == "dev-only-secret":
        raise RuntimeError("Configure a stable SECRET_KEY with at least 32 characters")
    preview = os.environ.get("CLOUD_PREVIEW_READ_ONLY", "true").lower()
    if preview not in {"true", "false"}:
        raise RuntimeError("CLOUD_PREVIEW_READ_ONLY must be true or false")
    app = create_app({
        "DATA_MODE": "v4", "MONGO_URI": uri, "MONGO_DB": "vibecart_ai",
        "SECRET_KEY": secret, "SESSION_COOKIE_NAME": "__session",
        "SESSION_COOKIE_SECURE": True,
        "ENABLE_CHECKOUT": preview == "false" and os.environ.get("ENABLE_CHECKOUT", "false").lower() == "true", "AI_RECOMMENDATIONS_ENABLED": False,
        "AI_SUMMARY_ENABLED": False, "AI_INSIGHT_FREE_TEXT_ENABLED": False,
    })
    app.config["CLOUD_PREVIEW_READ_ONLY"] = preview == "true"

    @app.before_request
    def preview_access():
        if not app.config["CLOUD_PREVIEW_READ_ONLY"]:
            return
        # Anonymous reads cannot emit member behavior events or enter admin routes.
        for key in ("user_id", "role", "name", "event_session"):
            session.pop(key, None)
        if request.method not in {"GET", "HEAD", "OPTIONS"} or request.path.startswith(
            ("/auth", "/admin", "/cart", "/checkout")
        ):
            abort(403, description="展示環境目前僅開放商品瀏覽。")

    # Reject preview writes before CSRF/auth handlers, with one predictable status.
    app.before_request_funcs[None].remove(preview_access)
    app.before_request_funcs[None].insert(0, preview_access)

    @app.after_request
    def private_responses(response):
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.get("/health/live")
    def health():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        try:
            db = get_db()
            db.command("ping")
            if not db.products.find_one({"schema_version": 4, "status": "active"}, {"_id": 1}):
                return {"status": "not_ready"}, 503
        except PyMongoError:
            return {"status": "not_ready"}, 503
        return {"status": "ready"}

    return app
