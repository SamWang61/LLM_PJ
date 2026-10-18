"""Private BSON snapshot export and localhost-only isolated restoration.

Source client is read only. Metadata is bracketed before/after snapshot reads;
server-assigned collection UUIDs detect replacement, but are not restored.
Never print source URIs, documents, validators, or complete private manifests.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct

from bson import BSON, json_util
from bson.codec_options import CodecOptions
from bson.raw_bson import RawBSONDocument
from pymongo import IndexModel


RAW = CodecOptions(document_class=RawBSONDocument)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS,
                           sort_keys=True, separators=(',', ':'))


def logical_metadata(row):
    # Compound key order is significant. Encode it as a list before sorting.
    indexes = []
    for definition in row['indexes']:
        item = dict(definition)
        item['key'] = list(item['key'].items())
        indexes.append(item)
    return {'name': row['name'], 'type': row['type'], 'options': row['options'],
            'indexes': sorted(indexes, key=lambda x: x['name'])}


def metadata(database, search=True):
    result = []
    for collection in sorted(database.list_collections(), key=lambda x: x['name']):
        require(collection['type'] == 'collection', 'Unsupported collection type')
        name = collection['name']
        require(not name.startswith('system.'), 'System collection needs separate policy')
        indexes = list(database[name].list_indexes())
        searches = list(database[name].aggregate([{'$listSearchIndexes': {}}], maxTimeMS=10000)) if search else []
        result.append({'name': name, 'type': collection['type'],
                       'options': collection.get('options', {}),
                       'uuid': collection.get('info', {}).get('uuid'),
                       'indexes': indexes, 'search_indexes': searches})
    return result


def export_snapshot(client, database_name, directory, search=True):
    directory = Path(directory)
    directory.mkdir()  # A prior attempt is never overwritten.
    db = client[database_name]
    before = metadata(db, search=search)
    require(before, 'Source database has no collections')
    rows = []
    with client.start_session(snapshot=True) as session:
        for number, schema in enumerate(before):
            name = schema['name']
            data_name = str(number).zfill(4) + '.bson'
            metadata_name = str(number).zfill(4) + '.metadata.bson'
            (directory / metadata_name).write_bytes(BSON.encode(schema))
            digest = hashlib.sha256()
            count = 0
            size = 0
            with (directory / data_name).open('xb') as output:
                with db.get_collection(name, codec_options=RAW).find(
                        {}, session=session, sort=[('_id', 1)],
                        collation={'locale': 'simple'}, batch_size=200) as cursor:
                    for document in cursor:
                        raw = document.raw
                        output.write(raw)
                        digest.update(raw)
                        size += len(raw)
                        count += 1
            rows.append({'collection': name, 'data': data_name, 'metadata': metadata_name,
                         'documents': count, 'bytes': size, 'sha256': digest.hexdigest(),
                         'metadata_sha256': file_hash(directory / metadata_name)})
        # PyMongo4.14 snapshot timestamp. Fail rather than fall back to ordinary reads.
        stamp = getattr(session, '_snapshot_time', None)
        require(stamp is not None, 'Snapshot timestamp was not pinned')
        snapshot = {'time': stamp.time, 'inc': stamp.inc}
    after = metadata(db, search=search)
    require(canonical(before) == canonical(after), 'Source metadata changed during export')
    report = {'version': 1, 'complete': True, 'database': database_name,
              'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'snapshot_timestamp': snapshot, 'metadata_stable': True,
              'search_metadata_read': search, 'source_version': client.server_info()['version'],
              'collections': rows, 'search_indexes': sum(len(x['search_indexes']) for x in before),
              'indexes': sum(len(x['indexes']) for x in before),
              'ttl_indexes': sum('expireAfterSeconds' in i for x in before for i in x['indexes']),
              'documents': sum(x['documents'] for x in rows)}
    with (directory / 'manifest.json').open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    return report


def bson_documents(path):
    with Path(path).open('rb') as stream:
        while True:
            prefix = stream.read(4)
            if not prefix:
                return
            require(len(prefix) == 4, 'Truncated BSON length')
            size = struct.unpack('<i', prefix)[0]
            require(5 <= size <= 16 * 1024 * 1024, 'Invalid BSON size')
            raw = prefix + stream.read(size - 4)
            require(len(raw) == size and raw[-1:] == b'\0', 'Truncated BSON document')
            yield RawBSONDocument(raw)


def validate_backup(directory):
    directory = Path(directory).resolve(strict=True)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest.get('version') == 1 and manifest.get('complete') is True,
            'Incomplete backup')
    require(manifest.get('search_indexes') == 0, 'Atlas Search definitions require an Atlas restore')
    names = set()
    files = set()
    schemas = []
    for row in manifest['collections']:
        require(row['collection'] not in names, 'Duplicate collection')
        names.add(row['collection'])
        for key in ('data', 'metadata'):
            name = row[key]
            require(re.fullmatch(r'\d{4}(?:\.metadata)?\.bson', name) and name not in files,
                    'Unsafe or duplicate backup path')
            files.add(name)
            path = directory / name
            require(not path.is_symlink() and path.resolve().parent == directory,
                    'Backup link rejected')
            expected = row['sha256'] if key == 'data' else row['metadata_sha256']
            require(file_hash(path) == expected, 'Backup hash differs')
        require((directory / row['data']).stat().st_size == row['bytes'], 'Data size differs')
        schema = BSON((directory / row['metadata']).read_bytes()).decode()
        require(schema['name'] == row['collection'] and schema['type'] == 'collection',
                'Collection metadata differs')
        require(not schema['search_indexes'], 'Search index cannot be restored locally')
        require(sum(1 for _ in bson_documents(directory / row['data'])) == row['documents'],
                'BSON document count differs')
        schemas.append(schema)
    require(bool(names), 'No collections in backup')
    return manifest, schemas


def require_local_target(client, database_name):
    require(re.fullmatch(r'sam_n14_restore_[a-f0-9]{32}', database_name),
            'Target must be a generated N14 restore database')
    address = client.address
    require(address is not None and address[0] == '127.0.0.1', 'Target must be explicit IPv4 localhost')
    options = client.admin.command('getCmdLineOpts')['parsed']
    require(options.get('net', {}).get('bindIp') == '127.0.0.1', 'Server must bind only localhost')
    require(client.admin.command({'getParameter': 1, 'ttlMonitorEnabled': 1})['ttlMonitorEnabled'] is False,
            'TTL monitor must be disabled during restoration')
    require(database_name not in client.list_database_names(), 'Target database already exists')


def restore_snapshot(client, database_name, directory):
    # Complete integrity checks happen before any target write.
    manifest, schemas = validate_backup(directory)
    require_local_target(client, database_name)
    directory = Path(directory)
    db = client[database_name]
    rows = []
    for row, schema in zip(manifest['collections'], schemas):
        collection = db.create_collection(schema['name'], **schema['options'])
        batch = []
        for doc in bson_documents(directory / row['data']):
            batch.append(doc)
            if len(batch) == 200:
                collection.insert_many(batch, ordered=True, bypass_document_validation=True)
                batch = []
        if batch:
            collection.insert_many(batch, ordered=True, bypass_document_validation=True)
        definitions = []
        for index in schema['indexes']:
            if index['name'] == '_id_':
                continue
            item = dict(index)
            keys = list(item.pop('key').items())
            item.pop('v', None)  # Server version is compared below.
            definitions.append(IndexModel(keys, **item))
        if definitions:
            collection.create_indexes(definitions)
        digest = hashlib.sha256()
        count = 0
        for document in db.get_collection(schema['name'], codec_options=RAW).find(
                {}, sort=[('_id', 1)], collation={'locale': 'simple'}):
            digest.update(document.raw)
            count += 1
        require(count == row['documents'] and digest.hexdigest() == row['sha256'],
                'Restored BSON content differs')
        rows.append({'collection': schema['name'], 'documents': count, 'sha256_equal': True})
    restored = metadata(db, search=False)
    require(canonical([logical_metadata(x) for x in schemas]) ==
            canonical([logical_metadata(x) for x in restored]), 'Restored options or indexes differ')
    return {'verified': True, 'collections': len(rows), 'documents': sum(x['documents'] for x in rows),
            'indexes': manifest['indexes'], 'ttl_indexes': manifest['ttl_indexes'],
            'validators_and_index_options_equal': True, 'raw_bson_hash_differences': 0,
            'ttl_monitor_disabled': True, 'source_database_contacted_by_restore': False,
            'target_database': database_name, 'collections_verified': rows,
            'target_version': client.server_info()['version']}
