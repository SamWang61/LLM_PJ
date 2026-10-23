"""Suspend fixed-target sharing after explicit owner approval; never restore it.

Private recovery state is saved before the first mutation. Restoration belongs
to a later, verified encryption/backup run and is deliberately absent here.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path

from drive_backup_acl import (Drive, DriveError, PROJECT, FOLDER, OWNER,
                             FOLDER_MIME, FILE_FIELDS, PERMISSION_FIELDS,
                             identifier, plan, write_private_json)

INLINE_FIELDS = FILE_FIELDS + ",shared,permissions(" + PERMISSION_FIELDS + ")"


def validate_scope(snapshot, source_ids=()):
    if not snapshot.get("complete"):
        raise ValueError("A complete ACL snapshot is required")
    captured = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - captured).total_seconds()
    if not -60 <= age <= 3600:
        raise ValueError("Revalidate the snapshot before changing permissions")
    if set(snapshot.get("additional_project_source_ids", [])) != set(source_ids):
        raise ValueError("Additional sources need independent current UI verification")
    nodes = snapshot["nodes"]
    roots = {PROJECT, FOLDER, *source_ids}
    if not roots <= nodes.keys():
        raise ValueError("Missing fixed source roots")
    for key in roots:
        expected = ("application/vnd.google-apps.project" if key == PROJECT else
                    FOLDER_MIME if key == FOLDER else "application/vnd.google-apps.document")
        if nodes[key].get("mimeType") != expected or nodes[key].get("trashed"):
            raise ValueError("Wrong source type or trashed source")
        if key in {PROJECT, FOLDER} and nodes[key].get("name") != "LLM_PJ":
            raise ValueError("Fixed target name changed")
    for key in nodes:
        current, seen = key, set()
        while current not in roots:
            if current in seen:
                raise ValueError("Cyclic target tree")
            seen.add(current)
            parents = nodes.get(current, {}).get("parents", [])
            if len(parents) != 1 or parents[0] not in nodes:
                raise ValueError("Unknown or external parent")
            current = parents[0]
        if key not in roots and current != FOLDER:
            raise ValueError("Object outside the verified folder tree")
    result = plan(snapshot)
    if not result["acl_plan_ready"]:
        raise ValueError("The original permissions cannot be restored exactly")
    return result


def permission_set(rows):
    ids = [row.get("id") for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate permission IDs")
    return {row["id"]: row for row in rows}


def check_owner(item):
    if (not item.get("ownedByMe") or item.get("trashed") or item.get("driveId")
            or item.get("shortcutDetails") or not item.get("capabilities", {}).get("canShare")
            or OWNER not in [o.get("emailAddress") for o in item.get("owners", [])]):
        raise DriveError("Target identity, ownership or sharing capability changed")


def owner_only(item):
    check_owner(item)
    rows = item.get("permissions")
    # files.permissions is the full list for shareable My Drive files. Missing
    # ACLs or shared-drive metadata never count as an empty permission list.
    if (not isinstance(rows, list) or len(rows) != 1 or item.get("shared") is not False
            or rows[0].get("role") != "owner" or rows[0].get("emailAddress") != OWNER
            or not rows[0].get("id")):
        raise DriveError("Non-owner access remains or the full ACL is unavailable")


def verify_isolation(drive, snapshot, source_ids=(), *, evidence_directory=None):
    # A list response can lag behind a verified parent permission removal.
    # Accept a disagreement only through the same bounded, independent endpoint
    # verification used by restoration; never repeat DELETE or infer access.
    from drive_backup_restore import normalized, reconcile_acl_readback
    if evidence_directory is not None:
        evidence_directory = Path(evidence_directory)
        evidence_directory.mkdir(exist_ok=False)
    def verified_owner(item):
        original = snapshot["nodes"].get(item.get("id"))
        if original is None:
            raise DriveError("Target inventory changed during isolation readback")
        expected_rows = [p for p in original.get("permissions", []) if p.get("role") == "owner"]
        if len(expected_rows) != 1:
            raise DriveError("Original owner identity is incomplete")
        expected = normalized(expected_rows)
        try:
            owner_only(item)
            if normalized(item["permissions"]) != expected:
                raise DriveError("Original owner identity changed")
            return
        except (DriveError, ValueError):
            if evidence_directory is None:
                raise
        key = identifier(item["id"])
        write_private_json(evidence_directory / (key + "-initial.json"), {
            "metadata": dict(item), "original_permissions": original["permissions"]})
        try:
            current_permissions = drive.permissions(key)
            reconcile_acl_readback(item, current_permissions, expected, drive, evidence_directory)
            owner_only(item)
        except (DriveError, ValueError) as error:
            raise DriveError("Non-owner isolation readback failed after independent verification") from error

    roots = {PROJECT, FOLDER, *source_ids}
    nodes = {}
    for key in roots:
        item = drive.request("GET", f"files/{identifier(key)}", params={
            "fields": INLINE_FIELDS, "includePermissionsForView": "published"})
        if item.get("id") != key:
            raise DriveError("Root readback ID mismatch")
        if any(item.get(field) != snapshot["nodes"][key].get(field)
               for field in ("name", "mimeType", "parents")):
            raise DriveError("Root identity changed; inspect the existing recovery plan")
        verified_owner(item)
        # Independently verify the three roots with the paginated ACL endpoint.
        rows = drive.permissions(key)
        expected = normalized([p for p in snapshot["nodes"][key]["permissions"] if p.get("role") == "owner"])
        if normalized(rows) != expected:
            raise DriveError("Root ACL endpoint still reports non-owner access")
        item["permissions"] = rows
        nodes[key] = item
    queue = [FOLDER]
    while queue:
        group, queue = queue[:20], queue[20:]
        query = "(" + " or ".join(f"'{identifier(key)}' in parents" for key in group) + ") and trashed=false"
        for item in drive.pages("files", "files", q=query, pageSize=1000,
                                fields=f"nextPageToken,incompleteSearch,files({INLINE_FIELDS})",
                                includePermissionsForView="published"):
            key = identifier(item.get("id"))
            if key in nodes or len(item.get("parents", [])) != 1 or item["parents"][0] not in group:
                raise DriveError("Duplicate or out-of-scope readback item")
            verified_owner(item)
            nodes[key] = item
            if item["mimeType"] == FOLDER_MIME:
                queue.append(key)
    if nodes.keys() != snapshot["nodes"].keys():
        raise DriveError("Target inventory changed; keep sharing suspended and reconcile")
    return {"checked_at": datetime.now(timezone.utc).isoformat(),
            "objects": len(nodes), "non_owner_grants": 0, "complete": True, "nodes": nodes}


def isolate(drive, snapshot, directory, source_ids=()):
    journal = directory / "journal.json"
    if journal.exists():
        raise ValueError("Existing recovery journal: inspect it rather than repeat mutations")
    result = validate_scope(snapshot, source_ids)
    identity = drive.request("GET", "about", params={"fields": "user(emailAddress)"})
    if identity.get("user", {}).get("emailAddress") != OWNER:
        raise DriveError("Wrong OAuth account")
    original = snapshot["nodes"]
    expected = {}
    # Check every directly shared object before the first DELETE.
    for key in {row["file_id"] for row in result["direct"]}:
        item = drive.metadata(key)
        check_owner(item)
        for field in ("id", "name", "mimeType", "parents"):
            if item.get(field) != original[key].get(field):
                raise DriveError("Directly shared object's identity or parents changed")
        current = permission_set(drive.permissions(key))
        if current != permission_set(original[key]["permissions"]):
            raise DriveError("Permissions changed since the snapshot")
        expected[key] = current
    write_private_json(directory / "original-acl.json", snapshot)
    write_private_json(directory / "restore-plan.json", result)
    state = {"started_at": datetime.now(timezone.utc).isoformat(),
             "phase": "prepared", "sharing_restored": False, "files_copied": 0,
             "owner_approved_extended_isolation": True, "operations": [], "complete": False}
    write_private_json(journal, state)
    try:
        grants = sorted(result["direct"], key=lambda x: (x["file_id"] != FOLDER,
                                                       x["file_id"] == PROJECT, x["file_id"], x["permission_id"]))
        for grant in grants:
            key, permission_id = grant["file_id"], grant["permission_id"]
            operation = {**grant, "status": "requested"}
            state["operations"].append(operation)
            state["phase"] = "revoking"
            write_private_json(journal, state)
            try:
                drive.request("DELETE", f"files/{identifier(key)}/permissions/{identifier(permission_id)}")
            except Exception as error:
                # A lost response is not a reason to replay a mutation.
                operation["response_error_type"] = type(error).__name__
            current = permission_set(drive.permissions(key))
            remaining = {k: v for k, v in expected[key].items() if k != permission_id}
            if current != remaining:
                raise DriveError("Deletion not verified or concurrent ACL change detected")
            expected[key] = current
            operation["status"] = "verified_absent"
            write_private_json(journal, state)
        state["phase"] = "root_permissions_removed"
        state["permissions_removed_at"] = datetime.now(timezone.utc).isoformat()
        write_private_json(journal, state)
        verified = verify_isolation(drive, snapshot, source_ids,
                                    evidence_directory=directory / "isolation-readback")
        write_private_json(directory / "isolated-acl.json", verified)
        state.update(phase="isolation_verified", complete=True,
                     verified_at=verified["checked_at"], verified_objects=verified["objects"],
                     non_owner_grants=0)
        write_private_json(journal, state)
        return state
    except BaseException as error:
        state.update(phase="failed_closed", error_type=type(error).__name__)
        write_private_json(journal, state)
        raise


@contextmanager
def execution_lock(private):
    import msvcrt
    with (private / "backup-execution.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def register_recovery(private, output):
    marker = private / "active-isolation.json"
    if marker.exists():
        raise ValueError("An active isolation exists; preserve its original recovery plan")
    write_private_json(marker, {"run_directory": str(output), "phase": "in_progress",
                               "owner_approved_extended_isolation": True,
                               "restore_only_after_remediation_and_cloud_verification": True})
    return marker


def verify_active(drive, private):
    """Read-only cloud recheck; retain the original ACL and recovery journal."""
    marker = private / "active-isolation.json"
    state = json.loads(marker.read_text(encoding="utf8"))
    output = Path(state["run_directory"]).resolve(strict=True)
    if not output.is_relative_to(private.resolve()) or output == private.resolve():
        raise ValueError("Recovery directory must remain in the private profile")
    snapshot = json.loads((output / "original-acl.json").read_text(encoding="utf8"))
    original_plan = json.loads((output / "restore-plan.json").read_text(encoding="utf8"))
    journal = json.loads((output / "journal.json").read_text(encoding="utf8"))
    if (not snapshot.get("complete") or not original_plan.get("acl_plan_ready")
            or not journal.get("owner_approved_extended_isolation")
            or journal.get("sharing_restored") or state.get("sharing_restored")):
        raise ValueError("Incomplete or already restored recovery state")
    import uuid
    verified = verify_isolation(drive, snapshot, snapshot.get("additional_project_source_ids", []),
        evidence_directory=output / ("readonly-isolation-recheck-" + uuid.uuid4().hex))
    # Rechecks never replace the immutable original ACL, plan or execution log.
    write_private_json(output / "latest-isolation-readback.json", verified)
    return {"phase": "isolation_verified", "complete": True,
            "verified_at": verified["checked_at"], "verified_objects": verified["objects"],
            "non_owner_grants": 0, "sharing_restored": False, "files_copied": 0}


def main():
    from drive_backup_auth import PRIVATE, session
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--private-output", type=Path)
    parser.add_argument("--project-source-file", action="append", default=[])
    parser.add_argument("--owner-approved-extended-isolation", action="store_true")
    parser.add_argument("--verify-active", action="store_true",
                        help="Read-only recheck of the saved active isolation; no ACL mutations")
    args = parser.parse_args()
    if args.verify_active:
        if args.snapshot or args.private_output or args.project_source_file or args.owner_approved_extended_isolation:
            parser.error("Active verification uses only the saved private recovery state")
        with execution_lock(PRIVATE):
            result = verify_active(Drive(session()), PRIVATE)
        print(json.dumps(result))
        return
    if not args.snapshot or not args.private_output or not args.owner_approved_extended_isolation:
        parser.error("Isolation needs a snapshot, new private output and explicit owner approval")
    source, output = args.snapshot.resolve(), args.private_output.resolve()
    if not source.is_relative_to(PRIVATE.resolve()) or not output.is_relative_to(PRIVATE.resolve()):
        parser.error("Snapshot and recovery evidence must remain in the private profile")
    with execution_lock(PRIVATE):
        if (PRIVATE / "active-isolation.json").exists():
            raise ValueError("Existing isolation: inspect recovery state before starting another run")
        output.mkdir(exist_ok=False)
        with source.open(encoding="utf8") as stream:
            snapshot = json.load(stream)
        validate_scope(snapshot, args.project_source_file)
        marker = register_recovery(PRIVATE, output)
        try:
            result = isolate(Drive(session()), snapshot, output, args.project_source_file)
        except BaseException:
            write_private_json(marker, {"run_directory": str(output), "phase": "inspect_failed_run",
                                       "sharing_restored": False})
            raise
        write_private_json(marker, {"run_directory": str(output), "phase": "suspended",
                                   "verified_at": result["verified_at"], "sharing_restored": False,
                                   "restore_only_after_remediation_and_cloud_verification": True})
        print(json.dumps({key: result[key] for key in (
            "phase", "complete", "verified_objects", "non_owner_grants", "sharing_restored", "files_copied")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"complete": False, "error_type": type(error).__name__, "sharing_restored": False}))
        raise SystemExit(1) from None
