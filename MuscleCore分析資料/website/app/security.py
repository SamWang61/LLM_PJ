"""Same-session CSRF protection for browser forms and authenticated JSON calls."""
import hmac
import secrets
from flask import abort, request, session


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def init_security(app):
    app.jinja_env.globals.update(csrf_token=csrf_token, operation_id=lambda: secrets.token_urlsafe(24))

    @app.before_request
    def protect_forms():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                abort(400, description="表單已失效，請重新載入頁面後再試。")
