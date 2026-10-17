"""Committed source, rather than checkout line endings, defines a Cloud build."""
import importlib.util
from pathlib import Path
import subprocess
import tarfile


SCRIPT = Path(__file__).with_name("prepare_cloud_source.py")
spec = importlib.util.spec_from_file_location("prepare_cloud_source", SCRIPT)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_package_uses_committed_bytes_when_checkout_has_crlf(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Cloud source test")
    paths = sorted(source.REQUIRED | {f"{source.WEBSITE}/app/static/css/main.css"})
    for name in paths:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"first\nsecond\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "source")
    css = root / source.WEBSITE / "app/static/css/main.css"
    css.write_bytes(b"first\r\nsecond\r\n")
    untracked = root / source.WEBSITE / "app/uncommitted.py"
    untracked.write_bytes(b"should never deploy\n")
    monkeypatch.setattr(source, "ROOT", root)

    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    count, digest = source.package(first)
    assert count == len(paths)
    assert source.package(second) == (count, digest)
    with tarfile.open(first, "r:gz") as archive:
        assert archive.extractfile("app/static/css/main.css").read() == b"first\nsecond\n"
        assert "app/uncommitted.py" not in archive.getnames()
