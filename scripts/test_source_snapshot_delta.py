import hashlib
import json
import zipfile

import pytest

from source_snapshot_delta import create_delta, restore_delta, safe_name


def baseline(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'keep.bin').write_bytes(b'\0\1kept')
    (source/'change.txt').write_text('before')
    (source/'deleted.txt').write_text('remove')
    files={p.name:{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in source.iterdir()}
    manifest={'version':1,'complete':True,'errors':[],'files':files}
    archive=tmp_path/'base.zip'
    with zipfile.ZipFile(archive,'x') as z:
        for p in source.iterdir():z.write(p,'LLM_PJ/'+p.name)
        z.writestr('manifest.json',json.dumps(manifest))
    return source,manifest,archive,hashlib.sha256(archive.read_bytes()).hexdigest()


def test_full_recovery_from_base_and_delta(tmp_path):
    source,manifest,base,digest=baseline(tmp_path)
    (source/'change.txt').write_text('after');(source/'deleted.txt').unlink();(source/'new.txt').write_text('new')
    delta=tmp_path/'delta.zip';created=create_delta(source,manifest,digest,delta)
    result=restore_delta(base,delta,tmp_path/'restored')
    assert result['verified'] and result['files']==3
    assert created['delta']['deleted']==['deleted.txt']
    assert (tmp_path/'restored'/'keep.bin').read_bytes()==b'\0\1kept'
    assert (tmp_path/'restored'/'change.txt').read_text()=='after'


@pytest.mark.parametrize('direction',['directory_to_file','file_to_directory'])
def test_tree_type_replacement_round_trip(tmp_path,direction):
    source=tmp_path/'source';source.mkdir()
    if direction=='directory_to_file':
        (source/'node').mkdir();(source/'node/old.txt').write_text('old')
    else:(source/'node').write_text('old')
    files={p.relative_to(source).as_posix():{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in source.rglob('*') if p.is_file()}
    manifest={'version':1,'complete':True,'errors':[],'files':files};archive=tmp_path/'base.zip'
    with zipfile.ZipFile(archive,'x') as z:
        for rel in files:z.write(source/rel,'LLM_PJ/'+rel)
        z.writestr('manifest.json',json.dumps(manifest))
    if direction=='directory_to_file':
        (source/'node/old.txt').unlink();(source/'node').rmdir();(source/'node').write_text('new file')
    else:
        (source/'node').unlink();(source/'node').mkdir();(source/'node/new.txt').write_text('new child')
    delta=tmp_path/'delta.zip'
    create_delta(source,manifest,hashlib.sha256(archive.read_bytes()).hexdigest(),delta)
    result=restore_delta(archive,delta,tmp_path/'restored')
    assert result['verified'] and result['files']==1


@pytest.mark.parametrize('name',['../out','/absolute','C:/absolute','a\\b','a/../b','a//b','a/.. /outside','.','CON','a.'])
def test_traversal_and_ambiguous_names_rejected(name):
    with pytest.raises(ValueError):safe_name(name)


def test_wrong_base_refused_before_destination_creation(tmp_path):
    source,manifest,base,_=baseline(tmp_path);delta=tmp_path/'delta.zip'
    create_delta(source,manifest,'0'*64,delta)
    with pytest.raises(ValueError,match='Base ZIP'):restore_delta(base,delta,tmp_path/'restore')
    assert not (tmp_path/'restore').exists()


def test_output_inside_source_refused(tmp_path):
    source,manifest,base,digest=baseline(tmp_path)
    with pytest.raises(ValueError,match='outside'):create_delta(source,manifest,digest,source/'delta.zip')


def test_existing_recovery_is_never_overwritten(tmp_path):
    source,manifest,base,digest=baseline(tmp_path);delta=tmp_path/'delta.zip'
    create_delta(source,manifest,digest,delta);destination=tmp_path/'existing';destination.mkdir()
    with pytest.raises(ValueError,match='already'):restore_delta(base,delta,destination)


def test_explicit_ephemeral_exclusions_only(tmp_path):
    source,manifest,base,digest=baseline(tmp_path)
    (source/'.env').write_text('private-example');(source/'~$draft.pptx').write_bytes(b'lock')
    cache=source/'MuscleCore分析資料/website/.pytest_cache';cache.mkdir(parents=True);(cache/'temp').write_text('cache')
    result=create_delta(source,manifest,digest,tmp_path/'delta.zip')
    assert '.env' in result['manifest']['files']
    assert len(result['manifest']['excluded'])==2
