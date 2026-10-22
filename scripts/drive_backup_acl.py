"""Raw Drive v3 ACL inventory and conservative restore planning.

Unlike normalized connector metadata, this retains permission IDs and details.
Inventory is read-only. Private reports must not be committed or uploaded.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import uuid

PROJECT = "1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5"
FOLDER = "1lXZv3hn3CgYmotpxgcna8i27wEodL8Gh"
OWNER = "cashsam@gmail.com"
FOLDER_MIME = "application/vnd.google-apps.folder"
API = "https://www.googleapis.com/drive/v3/"
PERMISSION_FIELDS = ("id,type,role,emailAddress,domain,allowFileDiscovery,"
                     "permissionDetails,expirationTime,deleted,pendingOwner,view")
FILE_FIELDS = ("id,name,mimeType,parents,trashed,ownedByMe,owners(emailAddress,permissionId),"
               "capabilities(canShare),driveId,shortcutDetails,inheritedPermissionsDisabled,"
               "size,md5Checksum,sha256Checksum,modifiedTime,version")


class DriveError(RuntimeError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid Drive ID")
    return value


class Drive:
    def __init__(self, session):
        self.session = session

    def request(self, method, path, **kwargs):
        from requests.exceptions import ConnectionError, Timeout, SSLError
        # All callers use relative, validated resource IDs; never forward tokens.
        if path.startswith("/") or ":" in path or ".." in path:
            raise ValueError("Invalid API path")
        for attempt in range(4):
            try:
                response = self.session.request(method, API + path, timeout=30,
                                                allow_redirects=False, **kwargs)
            except SSLError:
                raise DriveError("Drive TLS validation failed") from None
            except (ConnectionError, Timeout):
                if method == "GET" and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise DriveError("Drive transport failed; mutation outcome requires readback") from None
            if response.status_code in (429, 500, 502, 503, 504) and method == "GET" and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            if not 200 <= response.status_code < 300:
                # Google errors may include private names; do not echo response bodies.
                raise DriveError(f"Drive {method} HTTP {response.status_code}")
            return response.json() if response.content else {}
        raise DriveError("Drive retry budget exceeded")

    def pages(self, path, key, **params):
        seen = set()
        while True:
            page = self.request("GET", path, params=params)
            if page.get("incompleteSearch"):
                raise DriveError("Incomplete Drive search")
            if key not in page or not isinstance(page[key], list):
                raise DriveError("Missing collection in Drive response")
            yield from page[key]
            token = page.get("nextPageToken")
            if not token:
                break
            if token in seen:
                raise DriveError("Repeated pagination token")
            seen.add(token)
            params["pageToken"] = token

    def metadata(self, file_id):
        return self.request("GET", f"files/{identifier(file_id)}", params={
            "fields": FILE_FIELDS, "supportsAllDrives": "true"})

    def permissions(self, file_id):
        return list(self.pages(f"files/{identifier(file_id)}/permissions", "permissions",
                               fields=f"nextPageToken,permissions({PERMISSION_FIELDS})",
                               pageSize=100, supportsAllDrives="true",
                               includePermissionsForView="published"))

    def children(self, parent):
        return list(self.pages("files", "files", q=f"'{identifier(parent)}' in parents and trashed=false",
                               fields=f"nextPageToken,incompleteSearch,files({FILE_FIELDS})",
                               pageSize=1000, supportsAllDrives="true", includeItemsFromAllDrives="true"))


def inventory(drive, checkpoint=None, project_source_files=()):
    nodes = {}
    for root, mime in ((PROJECT, "application/vnd.google-apps.project"), (FOLDER, FOLDER_MIME)):
        item = drive.metadata(root)
        if item.get("id") != root or item.get("mimeType") != mime or item.get("name") != "LLM_PJ" or item.get("trashed"):
            raise DriveError("Fixed target identity mismatch")
        nodes[root] = item
    # These IDs must first be confirmed in the fixed project's source list.
    # A project reference is not a Drive parent-child relationship.
    for key in project_source_files:
        key = identifier(key)
        item = drive.metadata(key)
        if (key in nodes or item.get("id") != key or item.get("trashed")
                or item.get("mimeType") != "application/vnd.google-apps.document"):
            raise DriveError("Additional project source must be a distinct verified Google Doc")
        nodes[key] = item
    queue = [FOLDER]
    def progress(phase):
        if checkpoint:
            checkpoint({"schema": 1, "phase": phase, "complete": False,
                        "project_id": PROJECT, "folder_id": FOLDER,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "pending_folders": list(queue), "nodes": nodes})
    progress("discovering")
    while queue:
        parent = queue.pop(0)
        for item in drive.children(parent):
            key = identifier(item.get("id"))
            if key in nodes or parent not in item.get("parents", []):
                raise DriveError("Duplicate, cyclic or inconsistent target tree")
            nodes[key] = item
            if item.get("mimeType") == FOLDER_MIME:
                queue.append(key)
        progress("discovering")
    progress("reading_permissions")
    for index, item in enumerate(nodes.values(), 1):
        item["permissions"] = drive.permissions(item["id"])
        if index % 25 == 0:
            progress("reading_permissions")
    return {"schema": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
            "project_id": PROJECT, "folder_id": FOLDER, "nodes": nodes,
            "additional_project_source_ids": list(project_source_files),
            "complete": True}


def restore_body(permission):
    if not permission.get("id") or permission.get("type") not in {"user", "group", "domain", "anyone"}:
        raise ValueError("Missing permission ID or unsupported principal")
    if permission.get("role") not in {"reader", "commenter", "writer"}:
        raise ValueError("Unsupported role")
    if permission.get("deleted") or permission.get("pendingOwner") or permission.get("view"):
        raise ValueError("Non-restorable permission state")
    body = {key: permission[key] for key in ("type", "role")}
    kind = permission["type"]
    required = "emailAddress" if kind in {"user", "group"} else "domain" if kind == "domain" else None
    if required:
        if not permission.get(required):
            raise ValueError("Missing restoration identity")
        body[required] = permission[required]
    if kind in {"domain", "anyone"}:
        if not isinstance(permission.get("allowFileDiscovery"), bool):
            raise ValueError("Missing discovery setting")
        body["allowFileDiscovery"] = permission["allowFileDiscovery"]
    if permission.get("expirationTime"):
        expiry = datetime.fromisoformat(permission["expirationTime"].replace("Z", "+00:00"))
        if expiry <= datetime.now(timezone.utc):
            raise ValueError("Expired permission requires explicit review")
        body["expirationTime"] = permission["expirationTime"]
    return body


def my_drive_source(file_id, permission, nodes):
    """Resolve an omitted inheritedFrom using a fully verified single-parent chain.

    Google only populates inheritedFrom for shared-drive items. This does not
    guess from names: every edge and exact principal/role must be in the snapshot.
    """
    visited = set()
    current, grant = file_id, permission
    while True:
        if current in visited:
            raise ValueError("Cyclic inheritance chain")
        visited.add(current)
        item = nodes.get(current, {})
        if item.get("driveId") or item.get("inheritedPermissionsDisabled"):
            raise ValueError("Cannot resolve shared-drive or limited-access inheritance")
        details = grant.get("permissionDetails", [])
        if not details or any(not isinstance(d.get("inherited"), bool) for d in details):
            raise ValueError("Inheritance metadata missing")
        if all(not d["inherited"] for d in details):
            return current
        if any(not d["inherited"] for d in details):
            raise ValueError("Mixed direct and inherited permission requires review")
        parents = item.get("parents", [])
        if len(parents) != 1 or parents[0] not in nodes:
            raise ValueError("Inheritance source outside fixed target or unknown")
        parent = parents[0]
        explicit = {d["inheritedFrom"] for d in details if d.get("inheritedFrom")}
        if explicit and explicit != {parent}:
            raise ValueError("Conflicting inheritance source in parent chain")
        matching = [p for p in nodes[parent].get("permissions", [])
                    if p.get("id") == grant.get("id") and acl_semantics(p) == acl_semantics(grant)]
        if len(matching) != 1:
            raise ValueError("Inheritance parent grant missing, ambiguous or changed")
        current, grant = parent, matching[0]


def plan(snapshot):
    if snapshot.get("complete") is not True or snapshot.get("project_id") != PROJECT or snapshot.get("folder_id") != FOLDER:
        raise ValueError("Incomplete or wrong-target ACL snapshot")
    nodes = snapshot["nodes"]
    if not {PROJECT, FOLDER} <= nodes.keys():
        raise ValueError("Missing fixed targets")
    blockers, direct, inherited = [], [], []
    for file_id, item in nodes.items():
        if not item.get("ownedByMe") or OWNER not in [o.get("emailAddress") for o in item.get("owners", [])]:
            blockers.append({"id": file_id, "reason": "not_owned_by_expected_owner"})
        if item.get("driveId") or item.get("shortcutDetails") or not item.get("capabilities", {}).get("canShare"):
            blockers.append({"id": file_id, "reason": "unsupported_drive_shortcut_or_cannot_share"})
        permissions = item.get("permissions", [])
        if not any(p.get("role") == "owner" and p.get("id") and p.get("emailAddress") == OWNER for p in permissions):
            blockers.append({"id": file_id, "reason": "owner_permission_not_verified"})
        for p in permissions:
            if p.get("role") == "owner":
                continue
            try:
                body = restore_body(p)
                details = p.get("permissionDetails", [])
                if not details or any(not isinstance(d.get("inherited"), bool) for d in details):
                    raise ValueError("Inheritance metadata missing")
                if any(d["inherited"] for d in details):
                    # Mixed direct/inherited grants must not be collapsed into one source.
                    if any(not d["inherited"] for d in details):
                        raise ValueError("Mixed direct and inherited permission requires review")
                    parents = [d.get("inheritedFrom") for d in details]
                    resolution = "api_inheritedFrom"
                    if all(source is None for source in parents):
                        parents = [my_drive_source(file_id, p, nodes)]
                        resolution = "verified_my_drive_parent_chain"
                    if any(source not in nodes for source in parents):
                        raise ValueError("Inheritance source outside fixed target or unknown")
                    ancestors, pending = set(), list(item.get("parents", []))
                    while pending:
                        ancestor = pending.pop()
                        if ancestor in ancestors:
                            continue
                        ancestors.add(ancestor)
                        pending.extend(nodes.get(ancestor, {}).get("parents", []))
                    for source in parents:
                        if source == file_id or source not in ancestors:
                            raise ValueError("Inheritance source is not an ancestor")
                        matching = [q for q in nodes[source].get("permissions", [])
                                    if q.get("id") == p["id"] and q.get("type") == p["type"]
                                    and q.get("role") == p["role"]]
                        if not matching:
                            raise ValueError("Inheritance source grant missing or changed")
                    inherited.append({"file_id": file_id, "permission_id": p["id"], "sources": parents,
                                      "source_resolution": resolution})
                else:
                    direct.append({"file_id": file_id, "permission_id": p["id"], "restore": body})
            except (ValueError, TypeError) as error:
                blockers.append({"id": file_id, "reason": str(error)})
    return {"objects": len(nodes), "direct": direct, "inherited": inherited,
            "blockers": blockers, "acl_plan_ready": not blockers,
            "backup_completed": False, "mutations": 0}


def probe_permissions(drive, journal):
    """Test create/revoke/restore on one new EMPTY object, never the real target.

    The probe has no project bytes or credentials. It is trashed after checking
    that its final ACL is owner-only. An interrupted probe has a private journal.
    """
    if journal.exists():
        raise ValueError("Refusing to overwrite probe recovery state")
    state = {"run_id": str(uuid.uuid4()), "purpose": "empty_acl_probe",
             "project_mutations": 0, "bytes_uploaded": 0, "complete": False}

    def save(phase):
        state["phase"] = phase
        temporary = journal.with_suffix(".pending")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(journal)

    save("creating_empty_probe")
    item = drive.request("POST", "files", params={"fields": "id,name,mimeType,ownedByMe"},
                         json={"name": "LLM_PJ empty ACL probe " + state["run_id"],
                               "mimeType": FOLDER_MIME,
                               "appProperties": {"llm_pj_acl_probe": state["run_id"]}})
    file_id = identifier(item["id"])
    state["file_id"] = file_id
    save("probe_created")
    if not item.get("ownedByMe") or file_id in {PROJECT, FOLDER}:
        raise DriveError("Unexpected probe owner or identity")
    initial = drive.permissions(file_id)
    if len(initial) != 1 or initial[0].get("role") != "owner" or initial[0].get("emailAddress") != OWNER:
        raise DriveError("Empty probe is not owner-only")
    body = {"type": "anyone", "role": "reader", "allowFileDiscovery": False}
    save("creating_probe_grant")
    permission = drive.request("POST", f"files/{file_id}/permissions", params={"fields": PERMISSION_FIELDS}, json=body)
    state["permission"] = permission
    save("probe_granted")

    def read_grants():
        return [p for p in drive.permissions(file_id) if p.get("role") != "owner"]

    grants = read_grants()
    if len(grants) != 1 or acl_semantics(grants[0]) != body:
        raise DriveError("Probe grant readback mismatch")
    saved = grants[0]
    state["original_grant"] = saved
    save("revoking_probe_grant")
    drive.request("DELETE", f"files/{file_id}/permissions/{identifier(saved['id'])}")
    if read_grants():
        raise DriveError("Probe isolation readback failed")
    save("probe_isolated")
    drive.request("POST", f"files/{file_id}/permissions", params={"fields": PERMISSION_FIELDS}, json=restore_body(saved))
    restored = read_grants()
    if len(restored) != 1 or acl_semantics(restored[0]) != body:
        raise DriveError("Probe restoration readback failed")
    state["permission_id_preserved"] = restored[0]["id"] == saved["id"]
    state["restored_grant"] = restored[0]
    save("probe_restoration_verified")
    drive.request("DELETE", f"files/{file_id}/permissions/{identifier(restored[0]['id'])}")
    if read_grants():
        raise DriveError("Probe cleanup isolation failed")
    save("probe_owner_only")
    drive.request("PATCH", f"files/{file_id}", params={"fields": "id,trashed"}, json={"trashed": True})
    if not drive.metadata(file_id).get("trashed"):
        raise DriveError("Probe trash readback failed")
    state["complete"] = True
    save("verified_and_trashed")
    return {key: state[key] for key in ("complete", "project_mutations", "bytes_uploaded", "permission_id_preserved")}


def acl_semantics(permission):
    return {key: permission[key] for key in ("type", "role", "emailAddress", "domain", "allowFileDiscovery", "expirationTime")
            if key in permission}


def write_private_json(path, data):
    """Stream large snapshots and replace only after a complete write."""
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
        stream.write("\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--probe-empty-object", action="store_true",
                        help="Test ACL transitions on a new empty object; no real backup data")
    parser.add_argument("--project-source-file", action="append", default=[],
                        help="Google Doc ID independently verified in the fixed project's sources")
    args = parser.parse_args()
    from drive_backup_auth import PRIVATE, session
    destination = args.private_output.resolve()
    if not destination.is_relative_to(PRIVATE.resolve()):
        parser.error("Full ACL reports must stay inside the private backup profile")
    if destination.exists():
        parser.error("Use a new report directory; never overwrite recovery evidence")
    destination.mkdir(parents=True)
    drive = Drive(session())
    identity = drive.request("GET", "about", params={"fields": "user(emailAddress,permissionId)"})
    if identity.get("user", {}).get("emailAddress") != OWNER:
        raise DriveError("Authenticated account is not the approved owner")
    if args.probe_empty_object:
        print(json.dumps(probe_permissions(drive, destination / "probe.json")))
        return 0
    last_progress = [0.0]
    def checkpoint(data):
        write_private_json(destination / "checkpoint.json", data)
        if time.monotonic() - last_progress[0] >= 30:
            print(json.dumps({"phase": data["phase"], "objects": len(data["nodes"]),
                              "permissions_read": sum("permissions" in x for x in data["nodes"].values()),
                              "complete": False}), flush=True)
            last_progress[0] = time.monotonic()
    snapshot = inventory(drive, checkpoint, args.project_source_file)
    result = plan(snapshot)
    for name, data in (("acl.json", snapshot), ("plan.json", result)):
        write_private_json(destination / name, data)
    print(json.dumps({"objects": result["objects"], "direct_grants": len(result["direct"]),
                      "inherited_grants": len(result["inherited"]), "blockers": len(result["blockers"]),
                      "acl_plan_ready": result["acl_plan_ready"], "mutations": 0}))
    return int(not result["acl_plan_ready"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"complete": False, "error_type": type(error).__name__,
                          "backup_started": False}))
        raise SystemExit(1) from None
