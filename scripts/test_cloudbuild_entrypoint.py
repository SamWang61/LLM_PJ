"""The GitHub build must boot the committed root image before staging private 0%."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_image_uses_committed_repository_layout_before_build():
    config = json.loads((ROOT / "deploy/cloudbuild-github-preview.json").read_text(encoding="utf-8"))
    steps = config["steps"]
    prepare, build, boot, push, stage = steps
    assert '--commit "$COMMIT_SHA" --layout repository' in prepare["args"][1]
    assert 'test "$_SERVICE_NAME" = "vibecart-acceptance-pr21"' in prepare["args"][1]
    assert build["dir"] == ".cloud-preview"
    assert build["args"][build["args"].index("-f") + 1] == "Dockerfile"
    assert "--network=none" in boot["args"] and boot["args"].index("--entrypoint") > 0
    assert "/health/live" in boot["args"][-1]
    assert push["args"][0] == "push"
    assert stage["args"][:4] == ["run", "services", "update", "vibecart-acceptance-pr21"]
    assert "--no-traffic" in stage["args"] and "--tag=github-preview" in stage["args"]
    assert "--command=" in stage["args"] and "--args=" in stage["args"]
    assert "--region=asia-east1" in stage["args"]
    assert "vibecart-web" not in json.dumps(config)
