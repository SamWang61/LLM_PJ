import copy
from datetime import datetime, timedelta, timezone
import json

import pytest

import drive_backup_acl as acl
import drive_backup_isolation as isolation
from test_drive_backup_acl import owner, grant, node


@pytest.fixture
def snapshot():
    writer = grant(id="writer-id", type="user", role="writer", emailAddress="teammate@example.invalid")
    writer.pop("allowFileDiscovery")
    return {"complete": True, "captured_at": datetime.now(timezone.utc).isoformat(),
            "project_id": acl.PROJECT, "folder_id": acl.FOLDER,
            "additional_project_source_ids": [], "nodes": {
                acl.PROJECT: node(acl.PROJECT, "application/vnd.google-apps.project", permissions=[owner(), writer]),
                acl.FOLDER: node(acl.FOLDER, acl.FOLDER_MIME, permissions=[owner(), grant()]),
                "child": node("child", "text/plain", [acl.FOLDER], [owner(), grant(permissionDetails=[{"inherited": True}])])}}


class FakeDrive:
    def __init__(self, snapshot, fail_at=0, lost_response=False, residual=False, directory=None):
        self.nodes = copy.deepcopy(snapshot["nodes"])
        self.deletes = []
        self.fail_at = fail_at
        self.lost_response = lost_response
        self.residual = residual
        self.directory = directory

    def metadata(self, key):
        return copy.deepcopy(self.nodes[key])

    def permissions(self, key):
        return copy.deepcopy(self.nodes[key]["permissions"])

    def inline(self, key):
        item = self.metadata(key)
        item["shared"] = any(p["role"] != "owner" for p in item["permissions"])
        for p in item["permissions"]:
            p.pop("permissionDetails", None)
        return item

    def request(self, method, path, **kwargs):
        if path == "about":
            return {"user": {"emailAddress": acl.OWNER}}
        parts = path.split("/")
        if method == "GET":
            return self.inline(parts[1])
        assert method == "DELETE"  # No grant creation or automatic restoration.
        assert (self.directory / "original-acl.json").exists()
        assert (self.directory / "restore-plan.json").exists()
        state = json.loads((self.directory / "journal.json").read_text())
        assert state["operations"][-1]["status"] == "requested"
        self.deletes.append(path)
        if len(self.deletes) == self.fail_at:
            raise acl.DriveError("write rejected")
        key, permission_id = parts[1], parts[3]
        self.nodes[key]["permissions"] = [p for p in self.nodes[key]["permissions"] if p["id"] != permission_id]
        if key == acl.FOLDER and not self.residual:
            self.nodes["child"]["permissions"] = [owner()]
        if self.lost_response:
            raise acl.DriveError("response lost after successful delete")
        return {}

    def pages(self, path, key, **params):
        assert params["includePermissionsForView"] == "published"
        assert f"'{acl.FOLDER}' in parents" in params["q"]
        yield self.inline("child")


def test_suspend_after_durable_capture_and_verify_entire_tree(snapshot, tmp_path):
    api = FakeDrive(snapshot, directory=tmp_path)
    result = isolation.isolate(api, snapshot, tmp_path)
    assert result["phase"] == "isolation_verified"
    assert result["verified_objects"] == 3 and result["non_owner_grants"] == 0
    assert not result["sharing_restored"] and result["files_copied"] == 0
    assert len(api.deletes) == 2 and api.deletes[0].startswith(f"files/{acl.FOLDER}/")


def test_uncertain_delete_is_read_back_without_repeating_mutation(snapshot, tmp_path):
    api = FakeDrive(snapshot, lost_response=True, directory=tmp_path)
    result = isolation.isolate(api, snapshot, tmp_path)
    assert result["complete"] and len(api.deletes) == 2
    assert all(x["response_error_type"] == "DriveError" for x in result["operations"])


def test_failure_after_first_revoke_keeps_private_recovery_and_does_not_restore(snapshot, tmp_path):
    api = FakeDrive(snapshot, fail_at=2, directory=tmp_path)
    with pytest.raises(acl.DriveError):
        isolation.isolate(api, snapshot, tmp_path)
    result = json.loads((tmp_path / "journal.json").read_text())
    assert result["phase"] == "failed_closed" and not result["sharing_restored"]
    assert len(api.permissions(acl.FOLDER)) == 1 and len(api.permissions(acl.PROJECT)) == 2


def test_residual_child_access_never_counts_as_isolated(snapshot, tmp_path):
    api = FakeDrive(snapshot, residual=True, directory=tmp_path)
    with pytest.raises(acl.DriveError, match="Non-owner"):
        isolation.isolate(api, snapshot, tmp_path)
    assert json.loads((tmp_path / "journal.json").read_text())["phase"] == "failed_closed"


def test_changed_root_acl_blocks_all_writes(snapshot, tmp_path):
    api = FakeDrive(snapshot, directory=tmp_path)
    api.nodes[acl.PROJECT]["permissions"][1]["role"] = "reader"
    with pytest.raises(acl.DriveError, match="Permissions changed"):
        isolation.isolate(api, snapshot, tmp_path)
    assert not api.deletes


def test_existing_journal_cannot_be_overwritten(snapshot, tmp_path):
    (tmp_path / "journal.json").write_text("existing recovery")
    api = FakeDrive(snapshot, directory=tmp_path)
    with pytest.raises(ValueError, match="Existing recovery"):
        isolation.isolate(api, snapshot, tmp_path)
    assert (tmp_path / "journal.json").read_text() == "existing recovery" and not api.deletes


@pytest.mark.parametrize("change", ["stale", "external_parent", "unverified_source", "missing_owner", "partial"])
def test_untrusted_or_incomplete_scope_blocks_mutation(snapshot, tmp_path, change):
    if change == "stale":
        snapshot["captured_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    elif change == "external_parent":
        snapshot["nodes"]["child"]["parents"] = ["outside"]
    elif change == "unverified_source":
        snapshot["additional_project_source_ids"] = ["unknown"]
    elif change == "missing_owner":
        snapshot["nodes"]["child"]["permissions"] = [grant()]
    else:
        snapshot["complete"] = False
    api = FakeDrive(snapshot, directory=tmp_path)
    with pytest.raises(ValueError):
        isolation.isolate(api, snapshot, tmp_path)
    assert not api.deletes


@pytest.mark.parametrize("change", [{"permissions": []}, {"shared": True}, {"driveId": "shared"}, {"permissions": None}])
def test_inline_owner_only_requires_full_supported_acl(change):
    item = node("sample", "text/plain", permissions=[owner()])
    item.update(shared=False)
    item.update(change)
    with pytest.raises(acl.DriveError):
        isolation.owner_only(item)


def test_readback_cannot_silently_drop_a_saved_item(snapshot, tmp_path):
    api = FakeDrive(snapshot, directory=tmp_path)
    api.pages = lambda *a, **kw: iter(())
    with pytest.raises(acl.DriveError, match="inventory changed"):
        isolation.isolate(api, snapshot, tmp_path)


def test_second_run_cannot_replace_original_recovery_pointer(tmp_path):
    marker = isolation.register_recovery(tmp_path, tmp_path / "first")
    original = marker.read_bytes()
    with pytest.raises(ValueError, match="active isolation"):
        isolation.register_recovery(tmp_path, tmp_path / "second")
    assert marker.read_bytes() == original


def test_active_recheck_is_readonly_and_preserves_original_state(snapshot, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    isolation.register_recovery(tmp_path, output)
    api = FakeDrive(snapshot, directory=output)
    isolation.isolate(api, snapshot, output)
    protected = [output / name for name in ("original-acl.json", "restore-plan.json", "journal.json")]
    before = {path: path.read_bytes() for path in protected}
    api.deletes.clear()
    result = isolation.verify_active(api, tmp_path)
    assert result["verified_objects"] == 3 and not api.deletes
    assert all(path.read_bytes() == original for path, original in before.items())


def test_active_recheck_rejects_new_access_without_repairing_it(snapshot, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    isolation.register_recovery(tmp_path, output)
    api = FakeDrive(snapshot, directory=output)
    isolation.isolate(api, snapshot, output)
    api.deletes.clear()
    api.nodes["child"]["permissions"].append(grant())
    with pytest.raises(acl.DriveError, match="Non-owner"):
        isolation.verify_active(api, tmp_path)
    assert not api.deletes and len(api.permissions("child")) == 2


def test_active_recheck_rejects_external_recovery_directory(tmp_path):
    isolation.write_private_json(tmp_path / "active-isolation.json",
                                 {"run_directory": str(tmp_path.parent)})
    with pytest.raises(ValueError, match="private profile"):
        isolation.verify_active(None, tmp_path)


def test_root_rename_during_readback_fails_closed(snapshot, tmp_path):
    api = FakeDrive(snapshot, directory=tmp_path)
    isolation.isolate(api, snapshot, tmp_path)
    api.nodes[acl.FOLDER]["name"] = "unexpected rename"
    with pytest.raises(acl.DriveError, match="Root identity changed"):
        isolation.verify_isolation(api, snapshot)


class LaggedListDrive(FakeDrive):
    def __init__(self, snapshot, *, stale_permission_reads=0, fresh_change=None, **kwargs):
        super().__init__(snapshot, **kwargs)
        self.old_child = self.inline("child")
        self.stale_permission_reads = stale_permission_reads
        self.child_permission_reads = 0
        self.fresh_change = fresh_change

    def pages(self, path, key, **params):
        yield copy.deepcopy(self.old_child)

    def permissions(self, key):
        if key == "child":
            self.child_permission_reads += 1
            if self.child_permission_reads <= self.stale_permission_reads:
                return copy.deepcopy(self.old_child["permissions"])
        return super().permissions(key)

    def request(self, method, path, **kwargs):
        row = super().request(method, path, **kwargs)
        if method == "GET" and path == "files/child" and self.fresh_change:
            change = self.fresh_change
            if change == "extra_grant":
                row["permissions"].append(grant()); row["shared"] = True
            elif change == "shared_flag":
                row["shared"] = True
            elif change == "owner_id":
                row["permissions"][0]["id"] = "different-owner-id"
            elif change == "missing_owner_email":
                row["permissions"][0].pop("emailAddress")
            elif change == "missing_permissions":
                row.pop("permissions")
            elif change == "parent":
                row["parents"] = ["outside"]
            elif change == "type":
                row["mimeType"] = acl.FOLDER_MIME
        return row


def test_stale_shared_list_requires_two_fresh_owner_only_endpoints(snapshot, tmp_path):
    api = LaggedListDrive(snapshot, directory=tmp_path)
    result = isolation.isolate(api, snapshot, tmp_path)
    assert result["complete"] and len(api.deletes) == 2
    proof = json.loads((tmp_path / "isolation-readback" / "acl-reconciliation" / "child.json").read_text())
    assert proof["initial_metadata"]["shared"] is True
    assert len(proof["initial_metadata"]["permissions"]) == 2
    assert proof["complete"] and len(proof["attempts"]) == 1
    fresh = proof["attempts"][0]
    assert fresh["metadata"]["shared"] is False
    assert [p["role"] for p in fresh["complete_permissions"]] == ["owner"]
    saved = json.loads((tmp_path / "original-acl.json").read_text())
    assert len(saved["nodes"]["child"]["permissions"]) == 2


def test_isolation_read_retry_preserves_conflict_and_never_repeats_delete(snapshot, tmp_path, monkeypatch):
    import drive_backup_restore as restore
    monkeypatch.setattr(restore.time, "sleep", lambda _: None)
    api = LaggedListDrive(snapshot, stale_permission_reads=2, directory=tmp_path)
    result = isolation.isolate(api, snapshot, tmp_path)
    assert result["complete"] and len(api.deletes) == 2
    proof = json.loads((tmp_path / "isolation-readback" / "acl-reconciliation" / "child.json").read_text())
    assert proof["complete"] and len(proof["attempts"]) == 2
    assert any(p["role"] != "owner" for p in proof["attempts"][0]["complete_permissions"])


@pytest.mark.parametrize("change", ["extra_grant", "shared_flag", "owner_id",
                                    "missing_owner_email", "missing_permissions", "parent", "type"])
def test_isolation_disagreement_cannot_waive_access_or_identity(snapshot, tmp_path, monkeypatch, change):
    import drive_backup_restore as restore
    monkeypatch.setattr(restore.time, "sleep", lambda _: None)
    api = LaggedListDrive(snapshot, fresh_change=change, directory=tmp_path)
    with pytest.raises(acl.DriveError, match="Non-owner isolation"):
        isolation.isolate(api, snapshot, tmp_path)
    journal = json.loads((tmp_path / "journal.json").read_text())
    assert journal["phase"] == "failed_closed" and not journal["sharing_restored"]
    assert len(api.deletes) == 2
    proof = json.loads((tmp_path / "isolation-readback" / "acl-reconciliation" / "child.json").read_text())
    assert not proof["complete"] and 1 <= len(proof["attempts"]) <= 3


def test_repeated_isolation_audit_does_not_overwrite_prior_evidence(snapshot, tmp_path):
    api = LaggedListDrive(snapshot, directory=tmp_path)
    isolation.isolate(api, snapshot, tmp_path)
    path = tmp_path / "isolation-readback" / "acl-reconciliation" / "child.json"
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        isolation.verify_isolation(api, snapshot, evidence_directory=tmp_path / "isolation-readback")
    assert path.read_bytes() == original and len(api.deletes) == 2
