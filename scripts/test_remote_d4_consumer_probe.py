"""Offline safety checks; no cloud or MongoDB connection is opened."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import remote_d4_consumer_probe as probe
from bson import ObjectId


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


def test_synthetic_and_normal_fixtures_must_have_distinct_major_categories():
    first, second = ObjectId(), ObjectId()
    rows = [{'major_category_id': major, 'category_path': [major, ObjectId()]}
            for major in (first, first, second)]
    selected = probe.distinct_category_fixtures(iter(rows))
    assert [p['major_category_id'] for p in selected] == [first, second]
    with pytest.raises(RuntimeError, match='Two distinct'):
        probe.distinct_category_fixtures(rows[:2])


def test_leading_category_reads_product_identity_instead_of_assuming_fixture_id_leads():
    pid, major = ObjectId(), ObjectId()
    db = MagicMock(); db.products.find_one.return_value = {'major_category_id': major}
    assert probe.leading_major_category(db, [('/product/'+str(pid)+'?q=test', 'reason')]) == major
    db.products.find_one.assert_called_once_with({'_id': pid}, {'major_category_id': 1})
    with pytest.raises(RuntimeError): probe.leading_major_category(db, [])
    with pytest.raises(RuntimeError): probe.leading_major_category(db, [('https://other.invalid/login', '')])


def test_current_ranking_accepts_unrated_cold_start_and_detects_cross_category_leak():
    # Use the real ranking contract; do not create a Flask app or load .env.
    import sys
    from pathlib import Path
    from datetime import datetime, timezone
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'MuscleCore分析資料/website'))
    from app.services.storefront_ranking import recommendations_6_4
    now = datetime.now(timezone.utc)
    products = [{'_id': ObjectId(), 'major_category_id': ObjectId(),
                 'minor_category_id': ObjectId(), 'name': 'isolated fixture',
                 'status': 'active', 'stock': 10, 'is_ai_recommendable': True,
                 'rating_status': 'DEFAULT', 'rating_count': 0}
                for _ in range(2)]
    normal = probe.make_event(ObjectId(), products[0]['_id'], 'test', now, False)
    synthetic = [probe.make_event(normal['user_id'], products[1]['_id'], 'test', now, True)
                 for _ in range(1001)]
    assert recommendations_6_4(products, [], now=now)['personalized'] == []
    expected = recommendations_6_4(products, [normal], now=now)['personalized']
    assert expected[0]['product']['_id'] == products[0]['_id']
    assert recommendations_6_4(products, [normal, *synthetic], now=now)['personalized'] == expected
    leaked = [{**event, 'metadata': {}} for event in synthetic]
    assert recommendations_6_4(products, [normal, *leaked], now=now)['personalized'][0]['product']['_id'] == products[1]['_id']
