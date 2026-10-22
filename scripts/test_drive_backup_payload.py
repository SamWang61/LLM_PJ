import hashlib
import json
from pathlib import Path
import pytest
import drive_backup_payload as payload


@pytest.mark.parametrize('path', ['../x', '/outside', 'C:/x', 'a/../b', 'a\\b', 'a//b'])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError): payload.safe_relative(path)


def test_streaming_scanner_rejects_live_uri_but_preserves_placeholder():
    assert payload.secret_bytes(b'mongodb+srv://test-user:non-placeholder@cluster.test/db')
    assert not payload.secret_bytes(b'mongodb+srv://<username>:<password>@example/db')


def test_complete_snapshot_encrypts_private_paths_and_preserves_normal_bytes(tmp_path):
    root=tmp_path/'source'; root.mkdir()
    (root/'readme.md').write_bytes(b'hello')
    (root/'.env').write_bytes(b'private fixture only')
    (root/'.git').mkdir(); (root/'.git'/'config').write_bytes(b'git config')
    (root/'empty').mkdir()
    key=tmp_path/'key'; key.write_bytes(b'k'*32)
    manifest=payload.prepare(root,tmp_path/'private',key,workers=2)
    assert manifest['complete'] and len(manifest['files'])==3
    assert not manifest['files']['readme.md']['encrypted']
    assert manifest['files']['.env']['encrypted']
    assert manifest['files']['.git/config']['encrypted']
    assert payload.verify_source(root,manifest)['complete']
    (root/'readme.md').write_bytes(b'changed')
    with pytest.raises(ValueError,match='content changed'): payload.verify_source(root,manifest)


def test_new_files_and_empty_directory_changes_invalidate_manifest(tmp_path):
    root=tmp_path/'source'; root.mkdir(); (root/'a').write_bytes(b'a')
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    manifest=payload.prepare(root,tmp_path/'private',key)
    (root/'extra').mkdir()
    with pytest.raises(ValueError,match='tree changed'):payload.verify_source(root,manifest)


def test_private_output_or_key_inside_source_is_rejected(tmp_path):
    root=tmp_path/'source';root.mkdir();key=tmp_path/'key';key.write_bytes(b'k'*32)
    with pytest.raises(ValueError,match='separate'):payload.prepare(root,root/'out',key)


def test_exact_exclusion_does_not_exclude_siblings(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'cache').mkdir();(root/'cache'/'skip').write_bytes(b'a')
    (root/'cache-other').mkdir();(root/'cache-other'/'keep').write_bytes(b'b')
    result=payload.scan(root,['cache'])
    assert result['complete'] and list(result['files'])==['cache-other/keep']


def test_readable_staging_does_not_turn_missing_source_into_complete_backup(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir();(root/'ok').write_bytes(b'good')
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    real_scan=payload.scan
    def denied(*args,**kwargs):
        result=real_scan(*args,**kwargs)
        result.update(complete=False,errors=[{'path':'blocked','error':'PermissionError'}])
        return result
    monkeypatch.setattr(payload,'scan',denied)
    with pytest.raises(ValueError,match='completely read'):payload.prepare(root,tmp_path/'closed',key)
    manifest=payload.prepare(root,tmp_path/'partial',key,stage_readable_only=True)
    assert not manifest['complete'] and manifest['source_errors'] and manifest['exclusions']==[]
    with pytest.raises(ValueError):payload.verify_source(root,manifest)


def test_unchanged_ciphertext_is_reused_only_for_same_source_and_key(tmp_path):
    root=tmp_path/'source';root.mkdir();(root/'.env').write_bytes(b'fixture')
    key=tmp_path/'key';key.write_bytes(b'k'*32)
    first=payload.prepare(root,tmp_path/'first',key)
    second=payload.prepare(root,tmp_path/'second',key,prior_manifest=first)
    assert first['files']['.env']['payload']==second['files']['.env']['payload']
    key.write_bytes(b'n'*32)
    third=payload.prepare(root,tmp_path/'third',key,prior_manifest=first)
    assert first['files']['.env']['payload']!=third['files']['.env']['payload']
    (root/'.env').write_bytes(b'changed')
    fourth=payload.prepare(root,tmp_path/'fourth',key,prior_manifest=third)
    assert third['files']['.env']['plaintext']!=fourth['files']['.env']['plaintext']
