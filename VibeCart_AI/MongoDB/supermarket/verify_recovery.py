"""Read back complete v4 schema and the exact restored classroom catalog."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from bson import BSON, json_util
from bson.codec_options import CodecOptions

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from bootstrap_schema import connect
from schema_complete_v4 import verify_complete
from import_catalog import build, check_references


def main():
    source = json.loads((ROOT / 'source_catalog.json').read_text(encoding='utf-8'))
    expected = build(source)
    check_references(expected)
    with connect('.env') as client:
        db = client.vibecart_ai
        schema = verify_complete(db)
        for name, documents in expected.items():
            actual = {d['_id']: d for d in db[name].find({'_id': {'$in': [d['_id'] for d in documents]}})}
            assert len(actual) == len(documents), 'Missing catalog documents: ' + name
            for doc in documents:
                normalized = BSON.encode(doc).decode(codec_options=CodecOptions(tz_aware=True))
                assert normalized == actual[doc['_id']], 'Restored document differs: ' + name
        migrations = list(db.schema_migrations.find({}))
        assert len(migrations) == 4 and all(m['status'] == 'succeeded' for m in migrations)
        assert db.system_configs.count_documents({'config_key': 'recommendation_policy'}) == 1
        report = {'checked_at': datetime.now(timezone.utc).isoformat(),
            'database': 'vibecart_ai', 'replica_set': client.admin.command('hello')['setName'],
            'status': 'restored_and_verified', 'collections': len(schema),
            'strict_error_validators': len(schema),
            'custom_indexes': sum(len(c['indexes']) - 1 for c in schema),
            'total_indexes': sum(len(c['indexes']) for c in schema),
            'counts': {c['collection']: c['count'] for c in schema},
            'major_categories': db.categories.count_documents({'level': 1}),
            'minor_categories': db.categories.count_documents({'level': 2}),
            'exact_catalog_documents_verified': sum(len(v) for v in expected.values()),
            'reference_validation': 'passed', 'successful_migrations': len(migrations),
            'public_storefront_deployment': 'not verified; no hosted URL provided'}
        (ROOT / 'latest_status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (ROOT / 'recovery_20261005/schema_readback.json').write_text(json_util.dumps({
            'checked_at': report['checked_at'], 'collections': schema, 'migrations': migrations},
            ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
