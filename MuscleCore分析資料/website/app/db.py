from datetime import datetime, timezone
import os
from threading import Lock
import weakref
from flask import current_app, g
from pymongo import MongoClient


_pools = weakref.WeakSet()


class _MongoPool:
    """One lazy client per Flask app/worker; request teardown never closes it."""
    def __init__(self, uri):
        self.uri = uri
        self.client = None
        self.lock = Lock()

    def get_client(self):
        with self.lock:
            if self.client is None:
                # Retain network bounds and also bound waiting for a busy pool.
                self.client = MongoClient(self.uri, serverSelectionTimeoutMS=2500,
                    connectTimeoutMS=2500, socketTimeoutMS=2500, waitQueueTimeoutMS=2500)
            return self.client

    def close(self):
        with self.lock:
            if self.client is not None:
                self.client.close()
                self.client = None

    def after_fork(self):
        # A parent client's sockets/locks must never be used or closed in a child.
        self.client = None
        self.lock = Lock()


def _after_fork():
    for pool in list(_pools):
        pool.after_fork()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)


def get_db():
    if "db" not in g:
        client = current_app.extensions["mongo_pool"].get_client()
        g.db = client[current_app.config["MONGO_DB"]]
    return g.db


def close_db(_error=None):
    g.pop("db", None)


def init_db(app):
    pool = _MongoPool(app.config["MONGO_URI"])
    app.extensions["mongo_pool"] = pool
    _pools.add(pool)
    weakref.finalize(app, pool.close)
    app.teardown_appcontext(close_db)


def utcnow():
    return datetime.now(timezone.utc)

