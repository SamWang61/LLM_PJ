"""Independent v4 device sessions; only a digest is stored on the server."""
from datetime import timedelta
import hashlib
import hmac
import secrets
from bson import ObjectId
from flask import current_app
from ..db import utcnow


def token_digest(token):
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        return None
    return hashlib.sha256(token.encode()).hexdigest()


def fingerprint(user):
    content = str(user.get("password_hash", ""))
    return hmac.new(current_app.secret_key.encode(), content.encode(), hashlib.sha256).hexdigest()


def create_member_session(db, user):
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.auth_sessions.insert_one({"_id": token_digest(token), "schema_version": 4,
        "user_id": user["_id"], "auth_fingerprint": fingerprint(user),
        "created_at": now, "expires_at": now + timedelta(days=30)})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now}})
    return token


def valid_member_session(db, user, token):
    digest = token_digest(token)
    if not digest:
        return False
    row = db.auth_sessions.find_one({"_id": digest, "user_id": user["_id"],
        "expires_at": {"$gt": utcnow()}})
    return bool(row and hmac.compare_digest(row["auth_fingerprint"], fingerprint(user)))


def revoke_device_session(db, user_id, token):
    digest = token_digest(token)
    if digest:
        db.auth_sessions.delete_one({"_id": digest, "user_id": ObjectId(user_id)})


def revoke_user_sessions(db, user_id, *, mongo_session=None):
    """Trusted admin interface; share the transaction with disable/role changes."""
    return db.auth_sessions.delete_many({"user_id": ObjectId(user_id)}, session=mongo_session).deleted_count
