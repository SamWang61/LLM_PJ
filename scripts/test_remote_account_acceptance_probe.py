"""Safety gates for disposable account writes; no cloud or live database."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import remote_account_acceptance_probe as probe
from test_remote_d4_consumer_probe import config


@pytest.mark.parametrize("field,value", [
    ("mongo_uri", config()["mongo_uri"].replace("/vibecart_acceptance_pr21", "/vibecart_ai")),
    ("service_url", "https://vibecart-web-test.a.run.app"),
    ("image", "registry/web:latest"),
])
def test_rejects_production_before_connection(monkeypatch, field, value):
    connection = MagicMock()
    monkeypatch.setattr(probe, "MongoClient", connection)
    with pytest.raises(RuntimeError):
        probe.run({**config(), field: value})
    connection.assert_not_called()


def test_broad_roles_cannot_write_even_in_cleanup(monkeypatch, capsys):
    client = MagicMock()
    client.admin.command.return_value = {"authInfo": {
        "authenticatedUserRoles": [{"role": "atlasAdmin", "db": "admin"}]}}
    monkeypatch.setattr(probe, "MongoClient", MagicMock(return_value=client))
    assert probe.run(config()) == 1
    db = client[probe.DATABASE]
    db.users.insert_one.assert_not_called()
    db.users.update_many.assert_not_called()
    db.users.delete_many.assert_not_called()
    db.auth_sessions.delete_many.assert_not_called()
    assert "scope_not_verified" in capsys.readouterr().out


def test_session_retirement_still_runs_when_disable_fails():
    db = MagicMock()
    db.users.update_many.side_effect = RuntimeError("simulated write failure")
    db.auth_sessions.delete_many.return_value = SimpleNamespace(deleted_count=2)
    db.auth_sessions.count_documents.return_value = 0
    result = probe.disable_and_revoke(db, "ours", ["u"])
    assert result["verified"] is False and result["sessions_revoked"] is True
    db.users.update_many.assert_called_once()
    assert db.users.update_many.call_args.args[0] == {
        "_id": {"$in": ["u"]}, "acceptance_run": "ours"}
    db.auth_sessions.delete_many.assert_called_once_with({"user_id": {"$in": ["u"]}})


def test_cleanup_reads_both_scopes_and_reports_leftover_sessions():
    db = MagicMock()
    db.users.count_documents.side_effect = [0, 2, 0]
    db.users.delete_many.return_value = SimpleNamespace(deleted_count=2)
    db.auth_sessions.delete_many.return_value = SimpleNamespace(deleted_count=2)
    db.auth_sessions.count_documents.return_value = 1
    result = probe.cleanup(db, "ours", ["u", "v"])
    assert result["verified"] is False
    assert result["retirement"]["sessions_remaining"] == 1
    db.users.delete_many.assert_called_once_with({
        "_id": {"$in": ["u", "v"]}, "acceptance_run": "ours"})
    assert db.users.count_documents.call_count == 3


@pytest.mark.parametrize("status,location", [(200, ""), (302, "/"), (403, "")])
def test_denied_page_requires_login_redirect_not_any_200_or_redirect(status, location):
    session = MagicMock()
    session.get.return_value = SimpleNamespace(status_code=status, headers={"Location": location})
    with pytest.raises(RuntimeError):
        probe.protected(session, "https://private.invalid", "/cart", allowed=False)


def test_partial_fixture_failure_is_sanitized_and_cleanup_runs(monkeypatch, capsys):
    client = MagicMock()
    db = client[probe.DATABASE]
    client.admin.command.return_value = {"authInfo": {
        "authenticatedUsers": [{"user": "sam_pr21_acceptance_20261017"}],
        "authenticatedUserRoles": [{"role": "readWrite", "db": probe.DATABASE}]}}
    db.users.insert_one.side_effect = [None, ValueError("must-not-leak-password")]
    db.users.count_documents.return_value = 0
    db.auth_sessions.count_documents.return_value = 0
    db.users.delete_many.return_value = SimpleNamespace(deleted_count=1)
    db.auth_sessions.delete_many.return_value = SimpleNamespace(deleted_count=0)
    monkeypatch.setattr(probe, "MongoClient", MagicMock(return_value=client))
    assert probe.run(config()) == 1
    output = capsys.readouterr().out
    assert "must-not-leak-password" not in output and '"verified": true' in output
    assert db.users.insert_one.call_count == 2
    db.users.delete_many.assert_called_once()
    db.auth_sessions.delete_many.assert_called_once()
