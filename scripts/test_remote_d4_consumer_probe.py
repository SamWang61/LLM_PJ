"""Offline safety checks; no cloud or MongoDB connection is opened."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import remote_d4_consumer_probe as probe


def config():
    return {"mongo_uri": "mongodb+srv://sam_pr21_acceptance_20261017:unused@"
            "vibecart-ai-free.odqe25w.mongodb.net/vibecart_acceptance_pr21",
            "service_url": "https://vibecart-acceptance-pr21-test.a.run.app",
            "revision": "vibecart-acceptance-pr21-test",
            "image": "registry/web@sha256:" + "a" * 64}


@pytest.mark.parametrize("key,value", [
    ("mongo_uri", config()["mongo_uri"].replace("/vibecart_acceptance_pr21", "/vibecart_ai")),
    ("service_url", "https://vibecart-web-test.a.run.app"),
    ("image", "registry/web:latest"),
])
def test_unsafe_scope_is_rejected_before_any_connection(monkeypatch, key, value):
    client = MagicMock()
    monkeypatch.setattr(probe, "MongoClient", client)
    data = config()
    data[key] = value
    with pytest.raises(RuntimeError):
        probe.run(data)
    client.assert_not_called()


def test_rejects_broad_or_wrong_database_roles():
    client = MagicMock()
    info = {"authenticatedUsers": [{"user": probe.MONGO_USER, "db": "admin"}],
            "authenticatedUserRoles": [{"role": "readWrite", "db": probe.DATABASE}]}
    client.admin.command.return_value = {"authInfo": info}
    probe.verify_database_roles(client)
    for roles in ([{"role": "atlasAdmin", "db": "admin"}],
                  [{"role": "readWrite", "db": "vibecart_ai"}],
                  info["authenticatedUserRoles"] + [{"role": "dbAdmin", "db": probe.DATABASE}]):
        client.admin.command.return_value = {"authInfo": {**info, "authenticatedUserRoles": roles}}
        with pytest.raises(RuntimeError):
            probe.verify_database_roles(client)


def test_cleanup_is_scoped_and_every_collection_is_read_back():
    db = MagicMock()
    names = ["behavior_events", "auth_sessions", "users", "product_skus", "products"]
    for name in names:
        getattr(db, name).delete_many.return_value = SimpleNamespace(deleted_count=2)
        getattr(db, name).count_documents.return_value = 0
    result = probe.cleanup_probe(db, "unique-probe", ["u"], ["s"], ["p"])
    assert result["verified"] is True
    db.behavior_events.delete_many.assert_called_once_with({"metadata.probe_id": "unique-probe"})
    db.users.delete_many.assert_called_once_with({"_id": {"$in": ["u"]}, "acceptance_run": "unique-probe"})
    for name in names:
        getattr(db, name).count_documents.assert_called_once()
    db.users.delete_many.side_effect = RuntimeError("simulated cleanup failure")
    result = probe.cleanup_probe(db, "unique-probe", ["u"], ["s"], ["p"])
    assert result["verified"] is False
    assert result["users"] == "delete_failed"
