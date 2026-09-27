from datetime import datetime, timezone
from flask import current_app, g
from pymongo import MongoClient


def get_db():
    if "db" not in g:
        client = MongoClient(current_app.config["MONGO_URI"], serverSelectionTimeoutMS=2500)
        client.admin.command("ping")
        g.mongo_client = client
        g.db = client[current_app.config["MONGO_DB"]]
    return g.db


def close_db(_error=None):
    client = g.pop("mongo_client", None)
    g.pop("db", None)
    if client:
        client.close()


def init_db(app):
    app.teardown_appcontext(close_db)


def utcnow():
    return datetime.now(timezone.utc)

