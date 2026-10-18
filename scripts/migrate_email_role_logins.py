"""Explicit index migration. Existing users, validators and sessions are preserved."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'VibeCart_AI/MongoDB'))
from email_role_schema import MIGRATION, INDEX, OLD_INDEX


def apply(db):
    checksum = hashlib.sha256((ROOT / 'VibeCart_AI/MongoDB/email_role_schema.py').read_bytes()
                              + Path(__file__).read_bytes()).hexdigest()
    record = db.schema_migrations.find_one({'_id': MIGRATION})
    if record and (record.get('checksum') != checksum or record.get('status') != 'succeeded'):
        raise RuntimeError('Changed or incomplete email/role migration')
    expected = INDEX.document
    indexes = {i['name']: i for i in db.users.list_indexes()}
    prior = indexes.get(OLD_INDEX)
    if prior and (list(prior['key'].items()) != [('email', 1)] or prior.get('unique') is not True):
        raise RuntimeError('Unexpected existing email index')
    # Create protection for each role before relaxing email-only uniqueness.
    db.users.create_indexes([INDEX])
    actual = next(i for i in db.users.list_indexes() if i['name'] == expected['name'])
    if list(actual['key'].items()) != [('email', 1), ('role', 1)] or actual.get('unique') is not True:
        raise RuntimeError('Email/role unique index readback failed')
    if prior:
        db.users.drop_index(OLD_INDEX)
    if not record:
        now = datetime.now(timezone.utc)
        db.schema_migrations.insert_one({'_id': MIGRATION, 'schema_version': 2, 'checksum': checksum,
            'status': 'succeeded', 'started_at': now, 'completed_at': now,
            'counts': {'source': 0, 'target': 0, 'errors': 0}, 'error_code': None})
    return {'migration': MIGRATION, 'status': 'succeeded', 'users_unchanged': True,
            'index': expected['name'], 'unique': True}


if __name__ == '__main__':
    raise SystemExit('Run through provision_role_accounts.py with an explicit private credentials file')
