import copy
import os

import pytest

import drive_backup_acl as acl


def owner():
    return {"id": "owner-id", "type": "user", "role": "owner", "emailAddress": acl.OWNER}


def grant(**changes):
    return {"id": "reader-id", "type": "anyone", "role": "reader",
            "allowFileDiscovery": False, "permissionDetails": [{"inherited": False}], **changes}


def node(key, mime, parents=None, permissions=None):
    return {"id": key, "name": "LLM_PJ", "mimeType": mime, "parents": parents or [],
            "ownedByMe": True, "owners": [{"emailAddress": acl.OWNER}],
            "capabilities": {"canShare": True}, "permissions": permissions or [owner()]}


@pytest.fixture
def snapshot():
    return {"complete": True, "project_id": acl.PROJECT, "folder_id": acl.FOLDER,
            "nodes": {acl.PROJECT: node(acl.PROJECT, "application/vnd.google-apps.project"),
                      acl.FOLDER: node(acl.FOLDER, acl.FOLDER_MIME, permissions=[owner(), grant()])}}


def test_direct_public_restore_preserves_non_discoverability(snapshot):
    result = acl.plan(snapshot)
    assert result["acl_plan_ready"]
    assert result["direct"][0]["restore"] == {"type": "anyone", "role": "reader", "allowFileDiscovery": False}
    assert result["mutations"] == 0 and not result["backup_completed"]


def test_inherited_grant_is_not_a_second_direct_share(snapshot):
    p = grant(permissionDetails=[{"inherited": True, "inheritedFrom": acl.FOLDER}])
    snapshot["nodes"]["child"] = node("child", "text/plain", [acl.FOLDER], [owner(), p])
    result = acl.plan(snapshot)
    assert result["acl_plan_ready"] and len(result["inherited"]) == 1 and len(result["direct"]) == 1


@pytest.mark.parametrize("change", [
    {"id": None}, {"permissionDetails": []}, {"emailAddress": None, "type": "user"},
    {"domain": None, "type": "domain"}, {"allowFileDiscovery": None}, {"deleted": True},
    {"pendingOwner": True}, {"view": "published"}, {"role": "organizer"},
    {"expirationTime": "2020-01-01T00:00:00Z"},
    {"permissionDetails": [{"inherited": True, "inheritedFrom": "outside"}]},
    {"permissionDetails": [{"inherited": True}]},
    {"permissionDetails": [{"inherited": False}, {"inherited": True, "inheritedFrom": acl.PROJECT}]},
])
def test_non_restorable_permissions_block_before_mutations(snapshot, change):
    snapshot["nodes"][acl.FOLDER]["permissions"][1].update(change)
    result = acl.plan(snapshot)
    assert not result["acl_plan_ready"] and result["blockers"] and result["mutations"] == 0


@pytest.mark.parametrize("change", [{"ownedByMe": False}, {"driveId": "shared"},
                                    {"shortcutDetails": {"targetId": "outside"}},
                                    {"capabilities": {"canShare": False}}, {"permissions": []}])
def test_unowned_or_unmanaged_target_blocks(snapshot, change):
    snapshot["nodes"][acl.FOLDER].update(change)
    assert not acl.plan(snapshot)["acl_plan_ready"]


def test_private_grant_restores_identity_and_role():
    result = acl.restore_body(grant(type="user", role="writer", emailAddress="fixture@example.invalid"))
    assert result == {"type": "user", "role": "writer", "emailAddress": "fixture@example.invalid"}


@pytest.mark.parametrize("source", [acl.PROJECT, acl.FOLDER])
def test_unrelated_or_missing_inherited_source_grant_blocks(snapshot, source):
    p = grant(id="unmatched-id", permissionDetails=[{"inherited": True, "inheritedFrom": source}])
    snapshot["nodes"]["child"] = node("child", "text/plain", [acl.FOLDER], [owner(), p])
    assert not acl.plan(snapshot)["acl_plan_ready"]


@pytest.mark.parametrize("change", [{"complete": False}, {"project_id": "wrong"}, {"folder_id": "wrong"}, {"nodes": {}}])
def test_incomplete_inventory_is_never_ready(snapshot, change):
    snapshot.update(change)
    with pytest.raises(ValueError):
        acl.plan(snapshot)


class PagedDrive(acl.Drive):
    def __init__(self, pages):
        self.responses = iter(pages)
        self.calls = []

    def request(self, method, path, **kwargs):
        assert method == "GET"
        self.calls.append(copy.deepcopy(kwargs))
        return next(self.responses)


def test_all_pages_including_empty_page_are_consumed():
    api = PagedDrive([{"files": [], "nextPageToken": "one"},
                      {"files": [{"id": "a"}], "nextPageToken": "two"}, {"files": [{"id": "b"}]}])
    assert list(api.pages("files", "files")) == [{"id": "a"}, {"id": "b"}]
    assert api.calls[1]["params"]["pageToken"] == "one"


@pytest.mark.parametrize("pages", [[{"files": [], "incompleteSearch": True}], [{}],
                                   [{"files": [], "nextPageToken": "x"}, {"files": [], "nextPageToken": "x"}]])
def test_incomplete_or_looping_pagination_fails_closed(pages):
    with pytest.raises(acl.DriveError):
        list(PagedDrive(pages).pages("files", "files"))


@pytest.mark.parametrize("value", [None, "", "../outside", "x' or true", "https://example.invalid"])
def test_identifiers_cannot_inject_queries_or_token_destinations(value):
    with pytest.raises(ValueError):
        acl.identifier(value)


@pytest.mark.skipif(os.name != "nt", reason="DPAPI is Windows account-bound")
def test_dpapi_roundtrip_and_tamper_rejection():
    from drive_backup_auth import protect
    raw = b"private-test-fixture"
    encrypted = protect(raw)
    assert raw not in encrypted and protect(encrypted, True) == raw
    with pytest.raises(OSError):
        protect(encrypted[:-20], True)


class ProbeDrive:
    def __init__(self, fail_restore=False):
        self.grants = []
        self.calls = []
        self.trashed = False
        self.fail_restore = fail_restore
        self.posts = 0

    def request(self, method, path, **kwargs):
        self.calls.append((method, path))
        assert acl.PROJECT not in path and acl.FOLDER not in path
        if method == "POST" and path == "files":
            assert kwargs["json"]["mimeType"] == acl.FOLDER_MIME
            assert "parents" not in kwargs["json"] and "uploadType" not in kwargs.get("params", {})
            return {"id": "empty-probe", "ownedByMe": True}
        if method == "POST":
            self.posts += 1
            if self.fail_restore and self.posts == 2:
                raise acl.DriveError("Simulated restoration failure")
            self.grants = [grant()]
            return self.grants[0]
        if method == "DELETE":
            self.grants = []
        if method == "PATCH":
            assert not self.grants and kwargs["json"] == {"trashed": True}
            self.trashed = True
        return {}

    def permissions(self, file_id):
        assert file_id == "empty-probe"
        return [owner(), *copy.deepcopy(self.grants)]

    def metadata(self, file_id):
        return {"id": file_id, "trashed": self.trashed}


def test_empty_probe_exercises_restoration_and_finishes_private(tmp_path):
    import json
    api = ProbeDrive()
    journal = tmp_path / "probe.json"
    result = acl.probe_permissions(api, journal)
    assert result == {"complete": True, "project_mutations": 0, "bytes_uploaded": 0,
                      "permission_id_preserved": True}
    assert api.trashed and not api.grants
    assert json.loads(journal.read_text())["phase"] == "verified_and_trashed"


def test_failed_probe_retains_recovery_and_does_not_claim_completion(tmp_path):
    import json
    api = ProbeDrive(fail_restore=True)
    journal = tmp_path / "probe.json"
    with pytest.raises(acl.DriveError):
        acl.probe_permissions(api, journal)
    state = json.loads(journal.read_text())
    assert state["file_id"] == "empty-probe" and not state["complete"]
    assert state["original_grant"]["id"] == "reader-id"
    assert not api.grants and not api.trashed


def test_probe_never_overwrites_previous_recovery_state(tmp_path):
    journal = tmp_path / "probe.json"
    journal.write_text("previous")
    api = ProbeDrive()
    with pytest.raises(ValueError):
        acl.probe_permissions(api, journal)
    assert not api.calls and journal.read_text() == "previous"


class Transport:
    def __init__(self, responses):
        self.responses, self.calls = iter(responses), []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


def response(status=200):
    from types import SimpleNamespace
    return SimpleNamespace(status_code=status, content=b"{}", json=lambda: {"ok": True})


def test_read_transport_and_retryable_http_failures_are_bounded(monkeypatch):
    from requests.exceptions import ConnectionError, Timeout
    waits = []
    monkeypatch.setattr(acl.time, "sleep", waits.append)
    transport = Transport([ConnectionError("private"), response(503), Timeout("private"), response()])
    assert acl.Drive(transport).request("GET", "files/test") == {"ok": True}
    assert waits == [1, 2, 4] and len(transport.calls) == 4
    assert all(c[1]["timeout"] == 30 and c[1]["allow_redirects"] is False for c in transport.calls)
    transport = Transport([Timeout("private")] * 4)
    with pytest.raises(acl.DriveError, match="transport failed") as error:
        acl.Drive(transport).request("GET", "files/test")
    assert "private" not in str(error.value) and len(transport.calls) == 4


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_uncertain_mutation_is_not_retried(monkeypatch, method):
    from requests.exceptions import ConnectionError
    monkeypatch.setattr(acl.time, "sleep", lambda _: pytest.fail("Unexpected retry"))
    transport = Transport([ConnectionError("private"), response()])
    with pytest.raises(acl.DriveError, match="readback"):
        acl.Drive(transport).request(method, "files/test")
    assert len(transport.calls) == 1


def test_tls_failure_never_retries(monkeypatch):
    from requests.exceptions import SSLError
    monkeypatch.setattr(acl.time, "sleep", lambda _: pytest.fail("Unexpected retry"))
    transport = Transport([SSLError("private")])
    with pytest.raises(acl.DriveError, match="TLS validation failed"):
        acl.Drive(transport).request("GET", "files/test")
    assert len(transport.calls) == 1


def test_oauth_refresh_retries_only_transport_errors(monkeypatch):
    import drive_backup_auth as auth
    class NetworkFailure(Exception):
        pass
    class RevokedConsent(Exception):
        pass
    class Credential:
        def __init__(self, failures):
            self.failures, self.calls = iter(failures), 0
        def refresh(self, request):
            assert request == "request"
            self.calls += 1
            error = next(self.failures)
            if error:
                raise error
    waits = []
    monkeypatch.setattr(auth.time, "sleep", waits.append)
    credential = Credential([NetworkFailure(), NetworkFailure(), None])
    auth.refresh_credentials(credential, "request", NetworkFailure)
    assert credential.calls == 3 and waits == [1, 2]
    credential = Credential([NetworkFailure("private")] * 3)
    with pytest.raises(RuntimeError, match="credential retained") as error:
        auth.refresh_credentials(credential, "request", NetworkFailure)
    assert "private" not in str(error.value) and credential.calls == 3
    credential = Credential([RevokedConsent()])
    with pytest.raises(RevokedConsent):
        auth.refresh_credentials(credential, "request", NetworkFailure)
    assert credential.calls == 1


class InventoryDrive:
    def __init__(self, fail_permissions=False):
        self.fail_permissions = fail_permissions
    def metadata(self, key):
        mime = "application/vnd.google-apps.project" if key == acl.PROJECT else acl.FOLDER_MIME if key == acl.FOLDER else "application/vnd.google-apps.document"
        item = node(key, mime)
        item.pop("permissions")
        return item
    def children(self, key):
        return []
    def permissions(self, key):
        if self.fail_permissions:
            raise acl.DriveError("Simulated read failure")
        return [owner()]


def test_checkpoint_preserves_incomplete_discovery_on_failed_acl_read():
    saved = []
    with pytest.raises(acl.DriveError):
        acl.inventory(InventoryDrive(True), lambda data: saved.append(copy.deepcopy(data)))
    assert saved and all(s["complete"] is False for s in saved)
    assert saved[-1]["phase"] == "reading_permissions"
    assert set(saved[-1]["nodes"]) == {acl.PROJECT, acl.FOLDER}
    with pytest.raises(ValueError):
        acl.plan(saved[-1])


def test_verified_project_source_is_included_without_guessing_parenthood():
    result = acl.inventory(InventoryDrive(), project_source_files=["verified-doc"])
    assert result["complete"] and result["additional_project_source_ids"] == ["verified-doc"]
    assert result["nodes"]["verified-doc"]["parents"] == []
    assert acl.plan(result)["objects"] == 3


def test_duplicate_source_refuses_inventory():
    with pytest.raises(acl.DriveError):
        acl.inventory(InventoryDrive(), project_source_files=[acl.FOLDER])


def test_my_drive_inheritance_resolves_only_verified_parent_grants(snapshot):
    inherited = grant(permissionDetails=[{"inherited": True}])
    snapshot["nodes"]["subfolder"] = node("subfolder", acl.FOLDER_MIME, [acl.FOLDER], [owner(), inherited])
    snapshot["nodes"]["file"] = node("file", "text/plain", ["subfolder"], [owner(), inherited])
    result = acl.plan(snapshot)
    assert result["acl_plan_ready"] and len(result["inherited"]) == 2
    assert all(x["sources"] == [acl.FOLDER] and x["source_resolution"] == "verified_my_drive_parent_chain"
               for x in result["inherited"])


@pytest.mark.parametrize("change", [
    {"parents": ["outside"]}, {"parents": [acl.FOLDER, acl.PROJECT]},
    {"parents": ["file"]}, {"inheritedPermissionsDisabled": True},
    {"driveId": "shared"},
])
def test_unverifiable_my_drive_parent_chain_blocks(snapshot, change):
    inherited = grant(permissionDetails=[{"inherited": True}])
    item = node("file", "text/plain", [acl.FOLDER], [owner(), inherited])
    item.update(change)
    snapshot["nodes"]["file"] = item
    assert not acl.plan(snapshot)["acl_plan_ready"]


def test_my_drive_parent_grant_requires_exact_restore_semantics(snapshot):
    inherited = grant(role="writer", permissionDetails=[{"inherited": True}])
    snapshot["nodes"]["file"] = node("file", "text/plain", [acl.FOLDER], [owner(), inherited])
    assert not acl.plan(snapshot)["acl_plan_ready"]
