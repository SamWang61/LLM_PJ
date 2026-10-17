import io
import json
from pathlib import Path
import zipfile

import pytest
from v5_offline_bundle import pack, restore, verified_payload, safe_name, committed_bytes


@pytest.mark.parametrize('name', ['../escape.txt', '/absolute', 'C:/escape', 'a\\b', 'a/../b', 'NUL.txt', 'a./b'])
def test_unsafe_paths_rejected(name):
    with pytest.raises(ValueError):
        safe_name(name)


def test_deterministic_archive_restores_and_reads_back(tmp_path):
    files = {'index.html': b'<h1>offline</h1>', 'screenshots/S01-home.png': b'fixture'}
    first, manifest = pack(files, 'reviewed-sha')
    assert pack(files, 'reviewed-sha')[0] == first
    destination = tmp_path / 'fresh'
    assert restore(first, destination) == manifest
    assert all((destination / name).read_bytes() == data for name, data in files.items())


def rewrite(content, name, data):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as old, zipfile.ZipFile(out, 'w') as new:
        for n in old.namelist():
            new.writestr(n, data if n == name else old.read(n))
    return out.getvalue()


def test_tamper_rejected_before_any_restore_files_created(tmp_path):
    content, _ = pack({'index.html': b'approved'}, 'sha')
    content = rewrite(content, 'index.html', b'modified')
    destination = tmp_path / 'fresh'
    with pytest.raises(ValueError, match='integrity'):
        restore(content, destination)
    assert not destination.exists()


def test_unlisted_extra_file_rejected():
    content, _ = pack({'index.html': b'ok'}, 'sha')
    out = io.BytesIO(content)
    with zipfile.ZipFile(out, 'a') as archive:
        archive.writestr('unapproved.txt', 'extra')
    with pytest.raises(ValueError, match='file set'):
        verified_payload(out.getvalue())


def test_restore_refuses_existing_directory(tmp_path):
    content, _ = pack({'index.html': b'ok'}, 'sha')
    (tmp_path / 'keep.txt').write_text('keep')
    with pytest.raises(FileExistsError):
        restore(content, tmp_path)
    assert (tmp_path / 'keep.txt').read_text() == 'keep'


def test_windows_case_collision_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        pack({'A.txt': b'a', 'a.txt': b'b'}, 'sha')


def test_missing_lfs_payload_does_not_package_pointer(tmp_path, monkeypatch):
    oid = 'a' * 64
    def fake_git(root, *args):
        if args[0] == 'ls-tree':
            return b'100644 blob oid\tdeck.pdf\n'
        if args[0] == 'show':
            return f'version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize 10\n'.encode()
        return b'.git\n'
    monkeypatch.setattr('v5_offline_bundle.git', fake_git)
    with pytest.raises(ValueError, match='LFS payload unavailable'):
        committed_bytes(tmp_path, 'sha', 'deck.pdf')


def test_malicious_manifest_path_rejected_before_writes(tmp_path):
    content, manifest = pack({'index.html': b'ok'}, 'sha')
    manifest['files'][0]['path'] = '../outside'
    content = rewrite(content, 'manifest.json', json.dumps(manifest).encode())
    with pytest.raises(ValueError, match='Unsafe'):
        restore(content, tmp_path / 'fresh')
    assert not (tmp_path / 'fresh').exists()


def test_symbolic_link_member_rejected(tmp_path):
    content, _ = pack({'index.html': b'ok'}, 'sha')
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as old, zipfile.ZipFile(out, 'w') as new:
        for info in old.infolist():
            if info.filename == 'index.html':
                info.external_attr = 0o120777 << 16
            new.writestr(info, old.read(info.filename))
    with pytest.raises(ValueError, match='Unsafe'):
        restore(out.getvalue(), tmp_path / 'fresh')
    assert not (tmp_path / 'fresh').exists()
