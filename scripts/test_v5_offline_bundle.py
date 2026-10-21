import io
import json
from pathlib import Path
import zipfile

import pytest
from v5_offline_bundle import pack, restore, verified_payload, safe_name, committed_bytes
from v5_offline_bundle import note_links
import v5_offline_bundle as bundle


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


def test_offline_notes_follow_moved_files_and_pin_unbundled_citations():
    data = '[local](../slides/card.md#scope) [web](../../docs/evidence.md) [mail](mailto:team@example.invalid)'.encode()
    result = note_links(data, 'notes/runbook/README.md', 'README.md',
                        {'notes/slides/card.md': 'updates/card.md'}, 'fixed-sha').decode()
    assert '[local](updates/card.md#scope)' in result
    assert '[web](https://github.com/SamWang61/LLM_PJ/blob/fixed-sha/docs/evidence.md)' in result
    assert '[mail](mailto:team@example.invalid)' in result


def test_note_reference_cannot_escape_repository():
    with pytest.raises(ValueError, match='escapes'):
        note_links(b'[escape](../../outside)', 'notes/README.md', 'README.md', {}, 'sha')


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


@pytest.fixture
def current_assets(monkeypatch):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as deck:
        for i in range(1, 15):
            deck.writestr(f'ppt/slides/slide{i}.xml', '<slide/>')
    pptx, pdf = out.getvalue(), b'%PDF-reviewed-fixture'
    monkeypatch.setattr(bundle, 'CURRENT_PPTX_SHA256', bundle.sha256(pptx))
    monkeypatch.setattr(bundle, 'CURRENT_PDF_SHA256', bundle.sha256(pdf))
    assets = {bundle.DECK + '.pptx': pptx,
              bundle.CURRENT_FOLDER + 'VibeCart_AI_14頁閱讀版_2026-10-22.pdf': pdf,
              bundle.CURRENT_FOLDER + 'README.md': b'[PDF](VibeCart_AI_14%E9%A0%81%E9%96%B1%E8%AE%80%E7%89%88_2026-10-22.pdf)',
              bundle.CURRENT_FOLDER + '展示內容更新卡.md': b'current scope',
              'docs/CURRENT_CONTEXT.md': b'[scope](../some/dated-evidence.md)'}
    rows = []
    for i in range(1, 15):
        name = f'page-{i:02d}.png'
        data = b'\x89PNG\r\n\x1a\n' + bytes([i])
        assets[bundle.CURRENT_FOLDER + '投影片/' + name] = data
        rows.append({'file': name, 'bytes': len(data), 'sha256': bundle.sha256(data)})
    pages = {'profile': bundle.CURRENT_PROFILE, 'page_count': 14,
             'source_pptx_sha256': bundle.CURRENT_PPTX_SHA256,
             'source_pdf_sha256': bundle.CURRENT_PDF_SHA256, 'files': rows}
    assets[bundle.CURRENT_FOLDER + '投影片/pages.json'] = bundle.encode_json(pages)
    monkeypatch.setattr(bundle, 'committed_bytes', lambda root, commit, name: assets[name])
    return assets


def test_current_14_slide_package_restores_exact_whitelist(current_assets, tmp_path):
    files = bundle.current_source_files(tmp_path, 'pinned-commit')
    assert set(files) == {'presentation.pptx', 'presentation.pdf', 'README.md', 'index.html',
                          'slides.html', 'slides/pages.json', 'updates/current-context.md',
                          'updates/current-scope.md', *(f'slides/page-{i:02d}.png' for i in range(1, 15))}
    assert '14頁'.encode() in files['slides.html']
    assert b'[PDF](presentation.pdf)' in files['README.md']
    assert b'github.com/SamWang61/LLM_PJ/blob/pinned-commit/' in files['updates/current-context.md']
    first, manifest = pack(files, 'pinned-commit')
    assert pack(files, 'pinned-commit')[0] == first
    restored = tmp_path / 'offline'
    assert restore(first, restored) == manifest
    assert (restored / 'presentation.pptx').read_bytes() == current_assets[bundle.DECK + '.pptx']


@pytest.mark.parametrize('kind', ['pptx', 'pdf', 'page', 'index'])
def test_current_source_change_fails_before_packaging(current_assets, tmp_path, kind):
    if kind == 'pptx':
        name = bundle.DECK + '.pptx'
    elif kind == 'pdf':
        name = bundle.CURRENT_FOLDER + 'VibeCart_AI_14頁閱讀版_2026-10-22.pdf'
    elif kind == 'page':
        name = bundle.CURRENT_FOLDER + '投影片/page-14.png'
    else:
        name = bundle.CURRENT_FOLDER + '投影片/pages.json'
        index = json.loads(current_assets[name]); index['files'].pop()
        current_assets[name] = bundle.encode_json(index)
    if kind != 'index':
        current_assets[name] += b'unreviewed-change'
    with pytest.raises(ValueError, match='changed|integrity|contract'):
        bundle.current_source_files(tmp_path, 'pinned-commit')
