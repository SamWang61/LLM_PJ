"""Read-only immutable-main audit with a remote-head drift gate."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

import prepare_cloud_source as source

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def remote_main():
    return git("ls-remote", "origin", "refs/heads/main").decode().split()[0]


def require_stable_head(audited, before, after):
    if audited != before or audited != after:
        raise RuntimeError("Remote main moved: regenerate evidence for the new head")


def audit(baseline, deployed):
    before = remote_main()
    git("fetch", "origin", "main")
    audited = git("rev-parse", "FETCH_HEAD").decode().strip()
    require_stable_head(audited, before, remote_main())
    paths = [p.decode("utf-8") for p in git(
        "diff", "--name-only", "--diff-filter=ACMRT", "-z", baseline, audited
    ).split(b"\0") if p]

    def verify(path):
        blob = git("show", audited + ":" + path)
        url = "https://raw.githubusercontent.com/SamWang61/LLM_PJ/" + audited + "/" + quote(path, safe="/")
        with urlopen(url, timeout=45) as response:
            remote = response.read()
        if blob != remote:
            raise RuntimeError("Immutable remote content mismatch: " + path)
        return {"path": path, "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(), "commit_remote_equal": True}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(verify, paths))
    selected = source._sources(audited)
    deployed_entries = {p: oid for oid, p, _ in source._sources(deployed)}
    current_entries = {p: oid for oid, p, _ in selected}
    differences = sorted(p for p in current_entries.keys() | deployed_entries.keys()
                         if current_entries.get(p) != deployed_entries.get(p))
    with tempfile.TemporaryDirectory(prefix="llmpj-immutable-audit-") as folder:
        first, second = [Path(folder) / name for name in ("a.tar.gz", "b.tar.gz")]
        count, digest = source.package(first, audited)
        if source.package(second, audited) != (count, digest):
            raise RuntimeError("Build archive is not reproducible")
        manifest = []
        with tarfile.open(first, "r:gz") as archive:
            for oid, path, target in selected:
                blob = git("cat-file", "blob", oid)
                if archive.extractfile(target).read() != blob:
                    raise RuntimeError("Archive differs from Git blob: " + path)
                manifest.append({"path": path, "archive_path": target,
                                 "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
    after = remote_main()
    require_stable_head(audited, before, after)
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "audited_main": audited, "remote_main_before": before, "remote_main_after": after,
            "remote_head_stable": True, "baseline_main": baseline,
            "verified_files": len(files), "commit_remote_mismatches": 0, "files": files,
            "packaging": {"count": count, "deterministic_sha256": digest,
                          "repeat_archive_equal": True, "git_blob_mismatches": 0,
                          "deployed_source": deployed, "deployed_source_differences": differences,
                          "files": manifest},
            "scope": "Immutable main commit/remote bytes and reproducible archive; not dirty-checkout equality, LFS payload verification, deployment or business signoff"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--deployed-source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.baseline, args.deployed_source)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("audited_main", "verified_files", "remote_head_stable")}))
