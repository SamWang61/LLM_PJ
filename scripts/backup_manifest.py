"""Read-only file hashing and restored-tree comparison; no copy or ACL changes.

Output must be outside the scanned tree. Keep the manifest private: filenames
and hashes can identify private files even though their contents are absent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    before = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("Source changed during hashing")
    return {"size": after.st_size, "sha256": hasher.hexdigest()}


def scan(root):
    root = Path(root).resolve(strict=True)
    entries, errors = {}, []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            errors.append({"path": relative, "error": "link_requires_explicit_policy"})
        elif path.is_file():
            try:
                entries[relative] = digest(path)
            except (OSError, RuntimeError):
                errors.append({"path": relative, "error": "unreadable_or_changed"})
    return {"version": 1, "files": entries, "errors": errors, "complete": not errors}


def verify(root, manifest):
    root = Path(root).resolve(strict=True)
    errors = []
    if not manifest.get("complete") or manifest.get("errors"):
        errors.append({"error": "source_manifest_incomplete"})
    for relative, expected in manifest["files"].items():
        path = root / relative
        # Reject absolute/traversal paths and links to files outside the restore root.
        if not path.resolve().is_relative_to(root) or Path(relative).is_absolute():
            errors.append({"path": relative, "error": "unsafe_manifest_path"})
            continue
        try:
            if digest(path) != expected:
                errors.append({"path": relative, "error": "content_mismatch"})
        except (OSError, RuntimeError):
            errors.append({"path": relative, "error": "missing_unreadable_or_changed"})
    return {"verified": not errors, "files_checked": len(manifest["files"]), "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("scan", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "scan":
        if args.manifest.resolve().is_relative_to(args.root.resolve()):
            parser.error("Write the private manifest outside the scanned tree")
        report = scan(args.root)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"files_hashed": len(report["files"]), "complete": report["complete"], "error_count": len(report["errors"])}))
        return int(not report["complete"])
    report = verify(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps({"verified": report["verified"], "files_checked": report["files_checked"], "error_count": len(report["errors"])}))
    return int(not report["verified"])


if __name__ == "__main__":
    sys.exit(main())
