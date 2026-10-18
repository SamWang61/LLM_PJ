import json

import pytest
import backup_archive_parts as parts


@pytest.fixture
def transfer(tmp_path, monkeypatch):
    monkeypatch.setattr(parts, "PART_BYTES", 16)
    monkeypatch.setattr(parts, "BLOCK", 8)
    source = tmp_path / "ciphertext"
    source.write_bytes(bytes(range(71)))
    directory = tmp_path / "parts"
    report = parts.split(source, directory)
    return source, directory, report, tmp_path / "restored"


def test_ordered_roundtrip_and_no_overwrites(transfer):
    source, directory, report, output = transfer
    assert len(report["parts"]) == 5
    assert parts.join(directory, output)["verified"]
    assert source.read_bytes() == output.read_bytes()
    with pytest.raises(FileExistsError):
        parts.join(directory, output)
    with pytest.raises(FileExistsError):
        parts.split(source, directory)


@pytest.mark.parametrize("change", ["missing", "tamper", "swap", "traversal", "duplicate"])
def test_invalid_parts_never_publish(transfer, change):
    _, directory, report, output = transfer
    row = report["parts"][0]
    if change == "missing":
        (directory / row["name"]).unlink()
    elif change == "tamper":
        (directory / row["name"]).write_bytes(b"bad")
    elif change == "swap":
        report["parts"][0], report["parts"][1] = report["parts"][1], report["parts"][0]
    elif change == "traversal":
        row["name"] = "../ciphertext"
    else:
        report["parts"].append(row)
    (directory / "parts.json").write_text(json.dumps(report))
    with pytest.raises((ValueError, FileNotFoundError)):
        parts.join(directory, output)
    assert not output.exists()
    assert not list(output.parent.glob(".reassemble-*"))
