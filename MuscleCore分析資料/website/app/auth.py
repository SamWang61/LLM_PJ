from functools import wraps
from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, utcnow

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if not session.get("user_id"):
            flash("請先登入後再繼續。", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if session.get("role") != "admin":
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
            user = get_db().users.find_one({"email": email, "is_active": True})
        except PyMongoError:
            flash("目前無法連線至資料庫，請先啟動 MongoDB。", "danger")
            return render_template("auth/login.html"), 503
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=str(user["_id"]), name=user["name"], role=user["role"])
            target = "admin.dashboard" if user["role"] == "admin" else "store.home"
            return redirect(url_for(target))
        flash("帳號或密碼不正確。", "danger")
    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or "@" not in email or len(password) < 8:
            flash("請填寫有效姓名、Email 與至少 8 碼密碼。", "danger")
        else:
            db = get_db()
            if db.users.find_one({"email": email}):
                flash("此 Email 已註冊。", "warning")
            else:
                result = db.users.insert_one({
                    "name": name, "email": email,
                    "password_hash": generate_password_hash(password),
                    "role": "customer", "is_active": True,
                    "preferences": {"categories": [], "goals": []},
                    "created_at": utcnow(), "updated_at": utcnow(),
                })
                session.update(user_id=str(result.inserted_id), name=name, role="customer")
                return redirect(url_for("store.home"))
    return render_template("auth/register.html")


@bp.get("/logout")
def logout():
    session.clear()
    flash("您已安全登出。", "success")
    return redirect(url_for("store.home"))

