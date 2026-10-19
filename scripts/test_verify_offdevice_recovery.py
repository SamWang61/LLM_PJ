"""Failure gates for the N14 offline recovery wrapper; no real backup needed."""
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

import verify_offdevice_recovery as recovery


@pytest.mark.parametrize('member', ['../escape.txt', '/absolute.txt', 'C:/outside.txt'])
def test_capsule_rejects_path_escape(tmp_path, member):
    archive = tmp_path / 'bad.zip'
    with ZipFile(archive, 'w') as output:
        output.writestr(member, 'private')
    with pytest.raises(ValueError):
        recovery.safe_extract(archive, tmp_path / 'extract')
    assert not (tmp_path / 'escape.txt').exists()


def test_capsule_rejects_case_fold_duplicate(tmp_path):
    archive = tmp_path / 'duplicate.zip'
    with ZipFile(archive, 'w') as output:
        output.writestr('A/file', 'one')
        output.writestr('a/file', 'two')
    with pytest.raises(ValueError, match='Duplicate archive path'):
        recovery.safe_extract(archive, tmp_path / 'extract')


def test_mismatched_ciphertext_never_creates_restore_destination(tmp_path, monkeypatch):
    base = tmp_path / 'base.enc'
    latest = tmp_path / 'latest.enc'
    key = tmp_path / 'key.bin'
    base.write_bytes(b'not the approved backup')
    latest.write_bytes(b'not the approved backup')
    key.write_bytes(b'0' * 32)
    destination = tmp_path / 'restore'
    monkeypatch.setattr(sys, 'argv', ['verify_offdevice_recovery.py',
        '--base-ciphertext', str(base), '--latest-ciphertext', str(latest),
        '--key-file', str(key), '--destination', str(destination)])
    with pytest.raises(ValueError, match='ciphertext SHA-256 mismatch'):
        recovery.main()
    assert not destination.exists()
