"""Stable full-file inventory plus a delta against an authenticated private ZIP.

The resulting recovery chain needs BOTH the pinned base ZIP and this delta.
Only Office lock files and the explicit test cache are excluded, never .git,
ignored files, environments, or credentials. All artifacts must remain private.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

from backup_manifest import digest, verify

CACHE = 'MuscleCore分析資料/website/.pytest_cache'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    p = PurePosixPath(name)
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {prefix + str(n) for prefix in ('COM', 'LPT') for n in range(1, 10)}
    require(isinstance(name, str) and name and p.parts and not p.is_absolute()
            and '..' not in p.parts and '\\' not in name and ':' not in name
            and all(part.rstrip(' .') == part and part.split('.')[0].upper() not in reserved for part in p.parts)
            and p.as_posix() == name and '\0' not in name, 'Unsafe relative path')
    return name


def inventory(source):
    entries = {}
    excluded = []
    def failed(_error):
        raise ValueError('Source directory is unreadable')
    for parent, directories, files in os.walk(source, followlinks=False, onerror=failed):
        for name in list(directories):
            path = Path(parent) / name
            rel = path.relative_to(source).as_posix()
            if rel == CACHE:
                directories.remove(name)
                excluded.append({'path': rel, 'reason': 'Ephemeral pytest cache; access denied in source'})
            else:
                require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(),
                        'Source directory link rejected')
        for name in files:
            path = Path(parent) / name
            rel = safe_name(path.relative_to(source).as_posix())
            require(not path.is_symlink(), 'Source file link rejected')
            if name.startswith('~$') and path.suffix.lower() in ('.docx', '.pptx', '.xlsx'):
                excluded.append({'path': rel, 'reason': 'Office temporary lock; original document included'})
                continue
            info = path.stat()
            entries[rel] = (info.st_size, info.st_mtime_ns, info.st_ino)
    return entries, sorted(excluded, key=lambda x: x['path'])


def create_delta(source, base_manifest, base_zip_sha256, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    require(not output.is_relative_to(source), 'Output must be outside source')
    require(base_manifest.get('complete') is True and not base_manifest.get('errors'),
            'Base manifest incomplete')
    before, exclusions = inventory(source)
    files = {}
    changed = []
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1, allowZip64=True) as archive:
        for name in sorted(before):
            expected = digest(source / name)
            files[name] = expected
            if base_manifest['files'].get(name) != expected:
                h = hashlib.sha256()
                with (source / name).open('rb') as src, archive.open('files/' + name, 'w', force_zip64=True) as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        dst.write(block)
                        h.update(block)
                require(h.hexdigest() == expected['sha256'], 'Source changed while packing')
                changed.append(name)
        after, after_exclusions = inventory(source)
        require(before == after and exclusions == after_exclusions, 'Source inventory changed during snapshot')
        manifest = {'version': 1, 'complete': True, 'errors': [], 'files': files,
                    'excluded': exclusions}
        delta = {'version': 1, 'base_zip_sha256': base_zip_sha256,
                 'changed': changed, 'deleted': sorted(set(base_manifest['files']) - set(files))}
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
        archive.writestr('delta.json', json.dumps(delta, ensure_ascii=False))
    return {'manifest': manifest, 'delta': delta, 'archive': digest(output)}


def validate_names(names):
    seen = set()
    for name in names:
        safe_name(name)
        require(name.casefold() not in seen, 'Duplicate or case-colliding path')
        seen.add(name.casefold())


def restore_delta(base_zip, delta_zip, destination):
    destination = Path(destination).resolve()
    require(not destination.exists(), 'Destination already exists')
    with zipfile.ZipFile(delta_zip) as delta_archive:
        manifest = json.loads(delta_archive.read('manifest.json'))
        delta = json.loads(delta_archive.read('delta.json'))
        require(manifest.get('complete') is True and not manifest.get('errors')
                and manifest.get('version') == 1 and delta.get('version') == 1, 'Incomplete delta')
        validate_names(manifest['files'])
        validate_names(delta['changed'])
        validate_names(delta['deleted'])
        require(set(delta['changed']) <= set(manifest['files']), 'Changed path not in manifest')
        expected = {'manifest.json', 'delta.json'} | {'files/' + n for n in delta['changed']}
        actual = delta_archive.namelist()
        require(len(actual) == len(set(actual)) and set(actual) == expected, 'Unexpected delta ZIP members')
        require(digest(base_zip)['sha256'] == delta['base_zip_sha256'], 'Base ZIP hash mismatch')
        with zipfile.ZipFile(base_zip) as archive:
            base_manifest = json.loads(archive.read('manifest.json'))
            require(base_manifest.get('complete') is True and not base_manifest.get('errors'),
                    'Base manifest incomplete')
            validate_names(base_manifest['files'])
            require(set(delta['deleted']) == set(base_manifest['files']) - set(manifest['files']),
                    'Deleted paths differ from manifests')
            destination.mkdir()
            seen = set()
            for item in archive.infolist():
                if item.filename == 'manifest.json':
                    continue
                require(item.filename.startswith('LLM_PJ/'), 'Unexpected base ZIP member')
                name = safe_name(item.filename[len('LLM_PJ/'):])
                require(name in base_manifest['files'] and name not in seen
                        and not stat.S_ISLNK(item.external_attr >> 16), 'Unsafe base ZIP member')
                seen.add(name)
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as src, target.open('xb') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        dst.write(block)
            require(seen == set(base_manifest['files']), 'Base ZIP members incomplete')
        for name in delta['deleted']:
            (destination / name).unlink()
        for name in delta['changed']:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with delta_archive.open('files/' + name) as src, target.open('wb') as dst:
                for block in iter(lambda: src.read(1024 * 1024), b''):
                    dst.write(block)
    result = verify(destination, manifest)
    actual_files = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    require(result['verified'] and actual_files == set(manifest['files']), 'Full restored tree differs')
    return {'verified': True, 'files': len(manifest['files']), 'hash_differences': 0,
            'changed_files': len(delta['changed']), 'deleted_files': len(delta['deleted']),
            'base_zip_sha256': delta['base_zip_sha256'], 'exclusions': manifest.get('excluded', [])}
