"""Create the allowlisted Cloud Build archive without repository secrets/data."""
import argparse
import hashlib
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "MuscleCore分析資料" / "website"


def package(output):
    files = [(WEBSITE / name, name) for name in (
        "Dockerfile", ".dockerignore", "requirements-cloud.txt", "cloud_runtime.py"
    )]
    files.extend((WEBSITE / "app" / p.relative_to(WEBSITE / "app"),
                  "app/" + p.relative_to(WEBSITE / "app").as_posix())
                 for p in sorted((WEBSITE / "app").rglob("*")) if p.is_file()
                 and "__pycache__" not in p.parts
                 and not p.name.startswith(".env")
                 and p.suffix.lower() in {".py", ".html", ".css", ".js", ".svg", ".png", ".jpg", ".webp"})
    files.extend((ROOT / "VibeCart_AI" / "services" / name,
                  "VibeCart_AI/services/" + name)
                 for name in ("cart_service.py", "sku_cart_service.py"))
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Keep the build archive outside the repository")
    if output in [source.resolve() for source, _ in files]:
        raise ValueError("Output cannot replace a source file")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for source, target in files:
            archive.add(source, arcname=target, recursive=False)
    return len(files), hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count, digest = package(args.output)
    print(f"{count} allowlisted files; sha256={digest}")
