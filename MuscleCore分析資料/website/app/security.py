"""Same-session CSRF protection for browser forms and authenticated JSON calls."""
import hashlib
import hmac
import secrets
from flask import abort, g, request, session


CSRF_MESSAGE = "表單已失效，請重新載入頁面後再試。"
DUPLICATE_SAFE_ENDPOINTS = {"auth.login", "auth.logout"}


def supplied_token():
    return request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def remember_submitted_token(key):
    """Call right after login/logout cleared the session: keep only a digest of the token that was used."""
    token = supplied_token()
    if token:
        session[key] = token_digest(token)


def repeats_last_submission(key):
    """True only when this request carries exactly the token of the login/logout that already succeeded."""
    token, remembered = supplied_token(), session.get(key, "")
    return bool(token and remembered) and hmac.compare_digest(token_digest(token), remembered)


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
            supplied = supplied_token()
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                if request.endpoint in DUPLICATE_SAFE_ENDPOINTS:
                    # Login and logout clear the session, so a second click arrives with the old token.
                    # The view decides: if its outcome is already true it answers with that, else 400.
                    g.csrf_failed = True
                    return None
                abort(400, description=CSRF_MESSAGE)
