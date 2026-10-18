"""Boot a restored source tree on an internal, disposable Docker network only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, encoding="utf-8").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restored-root", type=Path, required=True)
    parser.add_argument("--runtime-image", required=True,
                        help="Existing local image containing Flask/PyMongo; never pulled")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.restored_root.resolve(strict=True)
    if not (root / "MuscleCore分析資料/website/app/__init__.py").is_file():
        parser.error("Restored website source is missing")
    image = json.loads(docker("image", "inspect", args.runtime_image))[0]["Id"]
    mongo_image = json.loads(docker("image", "inspect", "mongo:8"))[0]["Id"]
    marker = "sam-backup-" + uuid4().hex[:12]
    network, database, boot = (marker + suffix for suffix in ("-net", "-db", "-boot"))
    created = []
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "runtime_image_id": image, "mongo_image_id": mongo_image, "status": "failed"}
    # Reserve the report before creating resources. No existing file is replaced.
    with args.report.open("x", encoding="utf-8", newline="\n") as output:
        try:
            docker("network", "create", "--internal", network)
            created.append(("network", network))
            assert json.loads(docker("network", "inspect", network))[0]["Internal"]
            report["network_internal"] = True
            docker("run", "--pull=never", "--detach", "--name", database,
                   "--network", network, "--network-alias", "backup-db", mongo_image)
            created.append(("container", database))
            for _ in range(60):
                try:
                    docker("exec", database, "mongosh", "--quiet", "--eval", "db.adminCommand({ping:1}).ok")
                    break
                except subprocess.CalledProcessError:
                    time.sleep(.5)
            else:
                raise RuntimeError("Local backup database did not start")
            probe = Path(__file__).with_name("backup_restore_probe.py").resolve()
            docker("create", "--pull=never", "--name", boot, "--network", network,
                   "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                   "--mount", "type=bind,source=" + str(root) + ",target=/restore,readonly",
                   "--mount", "type=bind,source=" + str(probe) + ",target=/probe.py,readonly",
                   "--env", "SAM_BACKUP_INTERNAL_PROBE=true",
                   "--env", "PYTHONDONTWRITEBYTECODE=1", "--entrypoint", "python",
                   image, "/probe.py", "--restored-root", "/restore")
            created.append(("container", boot))
            info = json.loads(docker("inspect", boot))[0]
            assert info["HostConfig"]["ReadonlyRootfs"]
            assert all(not mount["RW"] for mount in info["Mounts"] if mount["Type"] == "bind")
            assert info["HostConfig"]["NetworkMode"] == network
            assert not info["HostConfig"]["PortBindings"]
            report["source_mount_readonly"] = True
            report["published_ports"] = 0
            raw = docker("start", "--attach", boot)
            code = json.loads(docker("inspect", boot))[0]["State"]["ExitCode"]
            assert code == 0, "Restored source boot failed"
            report["probe"] = json.loads(raw.splitlines()[-1])
            assert report["probe"]["status"] == "passed"
            assert report["probe"]["fixture_database_removed"]
            report["status"] = "passed"
        except Exception as error:
            report["error_type"] = type(error).__name__
        finally:
            failures = []
            for kind, name in reversed(created):
                try:
                    if kind == "container":
                        assert json.loads(docker("inspect", name))[0]["Name"] == "/" + name
                        docker("rm", "--force", name)
                    else:
                        assert json.loads(docker("network", "inspect", name))[0]["Name"] == name
                        docker("network", "rm", name)
                except Exception:
                    failures.append(kind)
            report["created_resources_removed"] = not failures
            if failures:
                report["status"] = "cleanup-failed"
            json.dump(report, output, indent=2)
            output.write("\n")
    print(json.dumps(report))
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
