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
        # All callers use relative, validated resource IDs; never forward tokens.
        if path.startswith("/") or ":" in path or ".." in path:
            raise ValueError("Invalid API path")
        for attempt in range(4):
            response = self.session.request(method, API + path, timeout=60,
                                            allow_redirects=False, **kwargs)
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


def inventory(drive):
    nodes = {}
    for root, mime in ((PROJECT, "application/vnd.google-apps.project"), (FOLDER, FOLDER_MIME)):
        item = drive.metadata(root)
        if item.get("id") != root or item.get("mimeType") != mime or item.get("name") != "LLM_PJ" or item.get("trashed"):
            raise DriveError("Fixed target identity mismatch")
        nodes[root] = item
    queue = [FOLDER]
    while queue:
        parent = queue.pop(0)
        for item in drive.children(parent):
            key = identifier(item.get("id"))
            if key in nodes or parent not in item.get("parents", []):
                raise DriveError("Duplicate, cyclic or inconsistent target tree")
            nodes[key] = item
            if item.get("mimeType") == FOLDER_MIME:
                queue.append(key)
    for item in nodes.values():
        item["permissions"] = drive.permissions(item["id"])
    return {"schema": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
            "project_id": PROJECT, "folder_id": FOLDER, "nodes": nodes,
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
                    inherited.append({"file_id": file_id, "permission_id": p["id"], "sources": parents})
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--probe-empty-object", action="store_true",
                        help="Test ACL transitions on a new empty object; no real backup data")
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
    snapshot = inventory(drive)
    result = plan(snapshot)
    for name, data in (("acl.json", snapshot), ("plan.json", result)):
        (destination / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"objects": result["objects"], "direct_grants": len(result["direct"]),
                      "inherited_grants": len(result["inherited"]), "blockers": len(result["blockers"]),
                      "acl_plan_ready": result["acl_plan_ready"], "mutations": 0}))
    return int(not result["acl_plan_ready"])


if __name__ == "__main__":
    raise SystemExit(main())
