import hashlib
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

import encrypted_backup as backup


@pytest.fixture
def case(tmp_path):
    keys = tmp_path / "keys"
    keys.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    key = keys / "key.bin"
    backup.keygen(key)
    plain = data / "archive.zip"
    plain.write_bytes(b"private-test-fixture\x00" * 140000)
    return plain, data / "archive.enc", key, data / "restored.zip"


def test_large_stream_roundtrip_is_exact_and_nonce_is_fresh(case):
    plain, encrypted, key, restored = case
    first = backup.encrypt(plain, encrypted, key)
    assert b"private-test-fixture" not in encrypted.read_bytes()
    other = encrypted.with_name("other.enc")
    backup.encrypt(plain, other, key)
    assert other.read_bytes() != encrypted.read_bytes()
    result = backup.decrypt(encrypted, restored, key)
    assert result["authenticated"]
    assert restored.read_bytes() == plain.read_bytes()
    assert first["plaintext"]["sha256"] == hashlib.sha256(plain.read_bytes()).hexdigest()


@pytest.mark.parametrize("position", [0, 9, 25, 50, 60, 1000, -1])
def test_any_tampering_rejects_without_plaintext_output(case, position):
    plain, encrypted, key, restored = case
    backup.encrypt(plain, encrypted, key)
    damaged = bytearray(encrypted.read_bytes())
    damaged[position] ^= 1
    encrypted.write_bytes(damaged)
    with pytest.raises((InvalidTag, ValueError)):
        backup.decrypt(encrypted, restored, key)
    assert not restored.exists()
    assert not list(restored.parent.glob(".decrypt-*"))


@pytest.mark.parametrize("change", ["short_header", "truncate", "append", "wrong_key"])
def test_invalid_length_and_wrong_key_never_publish(case, change):
    plain, encrypted, key, restored = case
    backup.encrypt(plain, encrypted, key)
    if change == "wrong_key":
        key.write_bytes(b"x" * 32)
    else:
        content = encrypted.read_bytes()
        encrypted.write_bytes({"short_header": content[:20],
                               "truncate": content[:-1], "append": content + b"x"}[change])
    with pytest.raises((InvalidTag, ValueError)):
        backup.decrypt(encrypted, restored, key)
    assert not restored.exists()
    assert not list(restored.parent.glob(".decrypt-*"))


def test_key_and_existing_output_are_never_overwritten(case):
    plain, encrypted, key, restored = case
    original_key = key.read_bytes()
    with pytest.raises(FileExistsError):
        backup.keygen(key)
    assert key.read_bytes() == original_key
    backup.encrypt(plain, encrypted, key)
    original = encrypted.read_bytes()
    with pytest.raises(FileExistsError):
        backup.encrypt(plain, encrypted, key)
    assert encrypted.read_bytes() == original
    restored.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        backup.decrypt(encrypted, restored, key)
    assert restored.read_bytes() == b"keep"


def test_output_race_does_not_replace_other_file(case, monkeypatch):
    plain, encrypted, key, restored = case
    backup.encrypt(plain, encrypted, key)
    original_link = backup.os.link

    def race(src, dst):
        Path(dst).write_bytes(b"concurrent-owner")
        original_link(src, dst)

    monkeypatch.setattr(backup.os, "link", race)
    with pytest.raises(FileExistsError):
        backup.decrypt(encrypted, restored, key)
    assert restored.read_bytes() == b"concurrent-owner"
    assert not list(restored.parent.glob(".decrypt-*"))


def test_source_change_is_detected_and_ciphertext_removed(case, monkeypatch):
    plain, encrypted, key, _ = case
    original_fingerprint = backup.fingerprint

    def change_after_hash(path):
        result = original_fingerprint(path)
        path.write_bytes(b"new version")
        return result

    monkeypatch.setattr(backup, "fingerprint", change_after_hash)
    with pytest.raises(ValueError, match="changed"):
        backup.encrypt(plain, encrypted, key)
    assert not encrypted.exists()


def test_key_must_be_separated_and_exactly_32_bytes(case):
    plain, encrypted, key, _ = case
    colocated = plain.with_name("unsafe-key.bin")
    colocated.write_bytes(key.read_bytes())
    with pytest.raises(ValueError, match="outside"):
        backup.encrypt(plain, encrypted, colocated)
    key.write_bytes(b"short")
    with pytest.raises(ValueError, match="32-byte"):
        backup.encrypt(plain, encrypted, key)


def test_empty_archive_roundtrip(case):
    plain, encrypted, key, restored = case
    plain.write_bytes(b"")
    backup.encrypt(plain, encrypted, key)
    backup.decrypt(encrypted, restored, key)
    assert restored.read_bytes() == b""
