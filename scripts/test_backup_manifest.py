import json
from backup_manifest import scan, verify


def test_full_manifest_includes_untracked_secret_named_files(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / ".env").write_text("isolated-test-only", encoding="utf-8")
    (root / "file.txt").write_text("original", encoding="utf-8")
    manifest = scan(root)
    assert manifest["complete"] and ".env" in manifest["files"]
    assert "isolated-test-only" not in json.dumps(manifest)
    assert verify(root, manifest)["verified"]
    (root / "file.txt").write_text("modified", encoding="utf-8")
    assert not verify(root, manifest)["verified"]


def test_restore_allows_destination_extra_files_but_rejects_missing(tmp_path):
    (tmp_path / "a").write_text("a")
    manifest = scan(tmp_path)
    (tmp_path / "extra").write_text("extra")
    assert verify(tmp_path, manifest)["verified"]
    (tmp_path / "a").unlink()
    assert not verify(tmp_path, manifest)["verified"]


def test_incomplete_or_traversal_manifest_never_verifies(tmp_path):
    assert not verify(tmp_path, {"complete": False, "files": {}, "errors": []})["verified"]
    manifest = {"complete": True, "files": {"../outside": {"size": 0, "sha256": ""}}, "errors": []}
    assert not verify(tmp_path, manifest)["verified"]
