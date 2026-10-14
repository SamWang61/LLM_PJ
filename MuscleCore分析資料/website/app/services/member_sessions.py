"""v4 single-login generation using the existing last_login_at BSON date.

Trusted admin callers may pass their MongoDB transaction session to revoke.
No bearer token, additional user field, or new collection is introduced.
"""
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from ..db import utcnow


def generation(value):
    if not isinstance(value, datetime):
        return None
    return (value.replace(tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(milliseconds=1)


def advance_generation(db, user_id, *, active_only=False, mongo_session=None):
    uid = ObjectId(user_id)
    query = {"_id": uid, "schema_version": 4}
    if active_only:
        query.update(status="active", is_active=True)
    for _ in range(8):
        user = db.users.find_one(query, session=mongo_session)
        if not user:
            return None
        previous = user.get("last_login_at")
        now = utcnow().replace(tzinfo=timezone.utc)
        if isinstance(previous, datetime):
            now = max(now, previous.replace(tzinfo=timezone.utc) + timedelta(milliseconds=1))
        # Match the generation and credentials/role read before this update.
        match = {**query, "last_login_at": previous, "role": user.get("role"),
                 "password_hash": user.get("password_hash")}
        updated = db.users.find_one_and_update(match,
            {"$set": {"last_login_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER, session=mongo_session)
        if updated:
            return updated
    raise PyMongoError("Member session generation contention")


def revoke_user_sessions(db, user_id, *, mongo_session=None):
    """Trusted server interface; caller must authorize the admin action first."""
    return advance_generation(db, user_id, mongo_session=mongo_session) is not None
