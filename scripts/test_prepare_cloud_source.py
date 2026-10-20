"""Committed source, rather than checkout line endings, defines a Cloud build."""
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import pytest


SCRIPT = Path(__file__).with_name("prepare_cloud_source.py")
spec = importlib.util.spec_from_file_location("prepare_cloud_source", SCRIPT)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.mark.parametrize("layout", ["flat", "repository"])
def test_package_uses_committed_bytes_when_checkout_has_crlf(tmp_path, monkeypatch, layout):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Cloud source test")
    css_name = f"{source.WEBSITE}/app/static/css/main.css"
    paths = sorted(source.REQUIRED | {"Dockerfile", ".dockerignore", css_name})
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
    count, digest = source.package(first, layout=layout)
    assert count == len(paths) - 2
    assert source.package(second, layout=layout) == (count, digest)
    with tarfile.open(first, "r:gz") as archive:
        css_target = "app/static/css/main.css" if layout == "flat" else css_name
        assert archive.extractfile(css_target).read() == b"first\nsecond\n"
        assert not any(name.endswith("uncommitted.py") for name in archive.getnames())
        assert "Dockerfile" in archive.getnames() and ".dockerignore" in archive.getnames()
        assert f"{source.WEBSITE}/Dockerfile" not in archive.getnames()
        assert "VibeCart_AI/services/cart_service.py" in archive.getnames()


def test_unknown_layout_refuses_before_creating_archive(tmp_path):
    output = tmp_path / "invalid.tar.gz"
    with pytest.raises(ValueError, match="Unknown cloud source layout"):
        source.package(output, layout="unsafe")
    assert not output.exists()
