"""Create a reproducible Cloud Build archive from committed Git blobs only."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
WEBSITE = "MuscleCore分析資料/website"
REQUIRED = {
    f"{WEBSITE}/{name}"
    for name in ("Dockerfile", ".dockerignore", "requirements-cloud.txt", "requirements-cloud-ai.txt", "cloud_runtime.py")
} | {
    f"VibeCart_AI/services/{name}"
    for name in ("cart_service.py", "sku_cart_service.py", "review_service.py")
}
APP_SUFFIXES = {".py", ".html", ".css", ".js", ".svg", ".png", ".jpg", ".webp"}


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _sources(commit):
    """Select regular committed files; never follow checkout bytes or untracked files."""
    selected = []
    for entry in _git("ls-tree", "-rz", commit).split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.split(b" ")
        path = raw_path.decode("utf-8")
        is_app = path.startswith(f"{WEBSITE}/app/")
        relative_app = path[len(f"{WEBSITE}/app/"):] if is_app else ""
        allowed_app = (
            is_app and "__pycache__" not in relative_app.split("/")
            and not Path(relative_app).name.startswith(".env")
            and Path(relative_app).suffix.lower() in APP_SUFFIXES
        )
        if path not in REQUIRED and not allowed_app:
            continue
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError(f"Source must be a regular Git file: {path}")
        target = path[len(WEBSITE) + 1:] if path.startswith(f"{WEBSITE}/") else path
        selected.append((object_id.decode("ascii"), path, target))
    missing = REQUIRED - {path for _, path, _ in selected}
    if missing:
        raise ValueError(f"Missing required committed source: {', '.join(sorted(missing))}")
    return sorted(selected, key=lambda item: item[2])


def package(output, commit="HEAD"):
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Keep the build archive outside the repository")
    sources = _sources(commit)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for object_id, _, target in sources:
                    data = _git("cat-file", "blob", object_id)
                    info = tarfile.TarInfo(target)
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(data))
    return len(sources), hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="HEAD", help="Commit containing the deployed source")
    args = parser.parse_args()
    count, digest = package(args.output, args.commit)
    print(f"{count} committed allowlisted files; sha256={digest}")
