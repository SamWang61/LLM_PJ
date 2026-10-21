from functools import wraps
import re
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from pymongo.errors import PyMongoError, DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, utcnow
from .services.member_sessions import create_member_session, valid_member_session, revoke_device_session, account_unexpired

bp = Blueprint("auth", __name__, url_prefix="/auth")


def safe_return_path(value):
    """Honor a local login destination without allowing external redirects."""
    if (value.startswith("/") and not value.startswith("//") and "\\" not in value
            and len(value) <= 2048 and all(ord(char) >= 32 for char in value)):
        return value
    return None


def current_member():
    if hasattr(g, "member"):
        return g.member
    g.member = None
    if not session.get("user_id"):
        return None
    try:
        uid = ObjectId(session["user_id"])
    except (ValueError, TypeError, InvalidId):
        session.clear()
        return None
    query = {"_id": uid, "is_active": True}
    if current_app.config["DATA_MODE"] == "v4":
        query.update(schema_version=4, status="active")
    user = get_db().users.find_one(query)
    if (not user or not account_unexpired(user) or user.get("role") not in {"admin", "customer"}
            or (current_app.config["DATA_MODE"] == "v4" and
                not valid_member_session(get_db(), user, session.get("member_session")))):
        session.clear()
        return None
    session.update(role=user["role"], name=user.get("display_name", user.get("name", "")))
    g.member = user
    return user


def start_member_session(user):
    token = None
    if current_app.config["DATA_MODE"] == "v4":
        prior_user_id = session.get("user_id")
        prior_token = session.get("member_session")
        current = get_db().users.find_one({"_id": user["_id"], "schema_version": 4,
            "status": "active", "is_active": True})
        if (not current or not account_unexpired(current)
                or current.get("password_hash") != user.get("password_hash")
                or current.get("role") != user.get("role")):
            return False
        user = current
        token = create_member_session(get_db(), user)
        if prior_user_id and prior_token:
            try:
                revoke_device_session(get_db(), prior_user_id, prior_token)
            except (TypeError, ValueError, InvalidId):
                # A malformed former cookie cannot prevent a valid new login.
                pass
    session.clear()
    session.update(user_id=str(user["_id"]), name=user.get("display_name", user.get("name", "")), role=user["role"])
    if current_app.config["DATA_MODE"] == "v4":
        session["member_session"] = token
    return True


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if not current_member():
            flash("請先登入後再繼續。", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(**kwargs):
        # Re-read permissions; a revoked administrator session must not retain access.
        user = current_member()
        if not user or user.get("role") != "admin":
            flash("此功能僅限管理員使用。", "danger")
            return redirect(url_for("store.home"))
        return view(**kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            query = {"email": email, "is_active": True}
            if current_app.config["DATA_MODE"] == "v4":
                query.update(schema_version=4, status="active")
            if current_app.config["DATA_MODE"] == "v4":
                query["role"] = {"$in": ["admin", "customer"]}
                candidates = list(get_db().users.find(query).limit(3))
            else:
                candidate = get_db().users.find_one(query)
                candidates = [candidate] if candidate else []
        except PyMongoError:
            flash("目前無法連線至資料庫，請先啟動 MongoDB。", "danger")
            return render_template("auth/login.html"), 503
        matches = []
        if len(email) <= 254 and 1 <= len(password) <= 1024 and len(candidates) <= 2:
            for candidate in candidates:
                try:
                    valid = check_password_hash(candidate.get("password_hash", ""), password)
                except (TypeError, ValueError):
                    valid = False
                if (valid and account_unexpired(candidate)
                        and candidate.get("role") in {"admin", "customer"}):
                    matches.append(candidate)
        # A password must identify exactly one role. Never trust a posted role.
        user = matches[0] if len(matches) == 1 else None
        if user and start_member_session(user):
            target = "admin.dashboard" if session["role"] == "admin" else "store.home"
            return redirect(safe_return_path(request.args.get("next", "")) or url_for(target))
        flash("帳號或密碼不正確。", "danger")
    return render_template("auth/login.html")


@bp.route("/password", methods=["GET", "POST"])
@login_required
def password_changes_disabled():
    """This teaching phase accepts credentials only through the offline manifest."""
    abort(403, description="此階段不開放會員或管理員自行修改密碼，帳號由指定文件建立。")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if (not 2 <= len(name) <= 100 or len(email) > 254
                or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
                or not 8 <= len(password) <= 1024):
            flash("請填寫有效姓名、Email 與至少 8 碼密碼。", "danger")
            return render_template("auth/register.html"), 400
        else:
            db = get_db()
            if db.users.find_one({"email": email}):
                flash("此 Email 已註冊。", "warning")
                return render_template("auth/register.html"), 409
            else:
                document = {
                    "name": name, "email": email,
                    "password_hash": generate_password_hash(password),
                    "role": "customer", "is_active": True,
                    "preferences": {"categories": [], "goals": []},
                    "created_at": utcnow(), "updated_at": utcnow(),
                }
                if current_app.config["DATA_MODE"] == "v4":
                    now = utcnow()
                    document.pop("name")
                    document.update(schema_version=4, display_name=name, auth_provider="local", firebase_uid=None,
                        status="active", member_level="basic", registered_at=now,
                        first_recommendation_generated_at=None, last_login_at=None,
                        preferences={"category_ids": [], "tags": [], "budget_min": None, "budget_max": None, "updated_at": None})
                try:
                    result = db.users.insert_one(document)
                except DuplicateKeyError:
                    flash("此 Email 已註冊。", "warning")
                    return render_template("auth/register.html"), 409
                document["_id"] = result.inserted_id
                if not start_member_session(document):
                    return redirect(url_for("auth.login"))
                return redirect(url_for("store.home"))
    return render_template("auth/register.html")


@bp.post("/logout")
def logout():
    user = current_member()
    if user and current_app.config["DATA_MODE"] == "v4":
        revoke_device_session(get_db(), user["_id"], session.get("member_session"))
    session.clear()
    flash("您已安全登出。", "success")
    return redirect(url_for("store.home"))
