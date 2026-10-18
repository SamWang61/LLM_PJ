import json
from pathlib import Path
import subprocess
import sys

import run_backup_restore_acceptance as runner


def test_host_probe_refuses_before_loading_restored_code(tmp_path):
    sentinel = tmp_path / "unexpected-execution"
    (tmp_path / "app.py").write_text("raise RuntimeError('must not import')")
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("backup_restore_probe.py")),
                             "--restored-root", str(tmp_path)], capture_output=True, text=True,
                            env={"SAM_BACKUP_INTERNAL_PROBE": "false"})
    assert result.returncode == 2
    assert "dedicated internal Docker" in result.stderr
    assert "must not import" not in result.stderr
    assert not sentinel.exists()


def test_external_network_rejected_before_container_creation(tmp_path, monkeypatch):
    source = tmp_path / "source"
    app = source / "MuscleCore分析資料/website/app/__init__.py"
    app.parent.mkdir(parents=True)
    app.write_text("raise RuntimeError('must not execute')")
    calls = []

    def docker(*args):
        calls.append(args)
        if args[:2] == ("image", "inspect"):
            return json.dumps([{"Id": "sha256:local-only"}])
        if args[:2] == ("network", "inspect"):
            return json.dumps([{"Internal": False, "Name": args[2]}])
        return "owned-resource"

    monkeypatch.setattr(runner, "docker", docker)
    report = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["runner", "--restored-root", str(source),
                        "--runtime-image", "local-image", "--report", str(report)])
    assert runner.main() == 1
    result = json.loads(report.read_text())
    assert result["status"] == "failed" and result["created_resources_removed"]
    assert not any(call[0] in {"run", "create"} for call in calls)
    assert any(call[:2] == ("network", "rm") for call in calls)


def test_existing_report_blocks_provisioning(tmp_path, monkeypatch):
    app = tmp_path / "MuscleCore分析資料/website/app/__init__.py"
    app.parent.mkdir(parents=True)
    app.write_text("")
    report = tmp_path / "existing.json"
    report.write_text("original evidence")
    calls = []

    def docker(*args):
        calls.append(args)
        assert args[:2] == ("image", "inspect")
        return json.dumps([{"Id": "sha256:local-only"}])

    monkeypatch.setattr(runner, "docker", docker)
    monkeypatch.setattr(sys, "argv", ["runner", "--restored-root", str(tmp_path),
                        "--runtime-image", "local-image", "--report", str(report)])
    try:
        runner.main()
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing evidence must not be replaced")
    assert report.read_text() == "original evidence"
    assert all(call[:2] == ("image", "inspect") for call in calls)
