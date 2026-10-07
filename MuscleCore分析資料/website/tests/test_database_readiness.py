"""Offline audit regression tests: no Atlas credentials or write methods."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
from pymongo import IndexModel

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.check_v4_database import audit, index_differences, SCHEMAS, INDEXES, MIGRATIONS


class Collection:
    def __init__(self, name):
        self.settings = {'validator': deepcopy(SCHEMAS[name]), 'validationLevel': 'strict', 'validationAction': 'error'}
        self.indexes = [{'name': '_id_', 'key': {'_id': 1}}]
        for model in INDEXES[name]:
            doc = deepcopy(model.document)
            if 'text' in doc['key'].values():
                doc['key'] = {'_fts': 'text', '_ftsx': 1}
                doc['weights'] = {'name': 1, 'description': 1}
            self.indexes.append(doc)
        self.documents = self.conforming = 0
        self.policies = 1
        self.rows = [{'_id': name, 'status': 'succeeded'} for name in MIGRATIONS]
        self.orphans = 0

    def options(self):
        return self.settings

    def list_indexes(self):
        return self.indexes

    def count_documents(self, query):
        if query.get('config_key'):
            return self.policies
        return self.conforming if '$jsonSchema' in query else self.documents

    def find(self, query, projection):
        assert projection == {'_id': 1, 'status': 1}
        return self.rows

    def aggregate(self, pipeline):
        assert pipeline[-1] == {'$count': 'orphans'}
        return [{'orphans': self.orphans}] if self.orphans else []


class Database:
    def __init__(self):
        self.collections = {name: Collection(name) for name in SCHEMAS}
        self.schema_migrations = self.collections['schema_migrations']
        self.system_configs = self.collections['system_configs']

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        return self.collections[name]


def test_current_schema_passes_read_only_without_any_write_api():
    report = audit(Database(), relationships=True)
    assert report['status'] == 'passed'
    assert len(report['collections']) == 27 and report['total_indexes'] == 86
    assert len(report['relationships']) == 12


@pytest.mark.parametrize('field,value', [('validator', {}), ('validationLevel', 'moderate'), ('validationAction', 'warn')])
def test_validator_drift_is_reported(field, value):
    db = Database()
    db['users'].settings[field] = value
    result = audit(db)
    assert result['status'] == 'failed'
    assert field in next(r for r in result['collections'] if r['name'] == 'users')['issues']


def test_missing_collection_and_multiple_errors_are_all_reported():
    db = Database()
    del db.collections['users']
    db['products'].settings['validationAction'] = 'warn'
    result = audit(db)
    assert result['status'] == 'failed'
    assert sum(bool(r['issues']) for r in result['collections']) == 2


@pytest.mark.parametrize('option,value', [('unique', False), ('sparse', True), ('expireAfterSeconds', 1),
                                          ('partialFilterExpression', {'active': True})])
def test_index_option_drift(option, value):
    model = IndexModel([('a', 1), ('b', -1)], unique=True)
    actual = deepcopy(model.document)
    actual[option] = value
    errors = index_differences({'_id_': {}, actual['name']: actual}, [model])
    assert any(e.endswith(':' + option) for e in errors)


def test_compound_key_order_and_text_weights():
    model = IndexModel([('a', 1), ('b', -1)])
    actual = deepcopy(model.document)
    actual['key'] = {'b': -1, 'a': 1}
    assert index_differences({'_id_': {}, actual['name']: actual}, [model])
    model = IndexModel([('name', 'text'), ('description', 'text')])
    actual = {'name': model.document['name'], 'key': {'_fts': 'text', '_ftsx': 1},
              'weights': {'name': 2, 'description': 1}}
    assert index_differences({'_id_': {}, actual['name']: actual}, [model])


def test_missing_and_extra_index_detected():
    db = Database()
    db['users'].indexes.pop()
    db['users'].indexes.append({'name': 'unexpected', 'key': {'x': 1}})
    assert audit(db)['status'] == 'failed'


def test_invalid_documents_and_orphans_are_counts_only():
    db = Database()
    db['products'].documents = 3
    db['products'].conforming = 2
    db['product_skus'].orphans = 1
    result = audit(db, relationships=True)
    assert result['status'] == 'failed' and 'orphan_references' in result['issues']
    assert next(r for r in result['relationships'] if r['source'] == 'product_skus')['orphans'] == 1


@pytest.mark.parametrize('change', ['missing', 'failed', 'extra'])
def test_migration_history(change):
    db = Database()
    if change == 'missing':
        db.schema_migrations.rows.pop()
    elif change == 'failed':
        db.schema_migrations.rows[0]['status'] = 'failed'
    else:
        db.schema_migrations.rows.append({'_id': 'unreviewed', 'status': 'succeeded'})
    assert audit(db)['status'] == 'failed'


def test_missing_policy_and_unknown_collection_require_review():
    db = Database()
    db.system_configs.policies = 0
    db.collections['unexpected'] = db['users']
    result = audit(db)
    assert 'expected_one_active_policy' in result['issues']
    assert 'unexpected_collections_review_required' in result['issues']


def test_relationship_pipeline_finds_only_dangling_v4_references():
    import mongomock
    from bson import ObjectId
    data = mongomock.MongoClient().test
    parent = data.products.insert_one({}).inserted_id
    data.product_skus.insert_many([
        {'schema_version': 4, 'product_id': parent},
        {'schema_version': 4, 'product_id': ObjectId()},
        {'schema_version': 3, 'product_id': ObjectId()}])
    db = Database()
    db['product_skus'].aggregate = data.product_skus.aggregate
    result = audit(db, relationships=True)
    assert next(r for r in result['relationships'] if r['source'] == 'product_skus')['orphans'] == 1
    assert result['status'] == 'failed'


def test_current_contract_requires_fifth_migration_and_overlay():
    db = Database()
    assert len(MIGRATIONS) == 5
    db.schema_migrations.rows = [r for r in db.schema_migrations.rows
        if r['_id'] != '20261005_05_synthetic_profile_v4']
    assert 'missing_or_unsuccessful_migration' in audit(db)['issues']
    from schema_complete_v4 import SCHEMAS as historical
    db['users'].settings['validator'] = deepcopy(historical['users'])
    result = audit(db)
    assert 'validator' in next(r for r in result['collections'] if r['name'] == 'users')['issues']


def test_overlay_keeps_batch_fields_for_orders_and_items():
    db = Database()
    for name in ('orders', 'order_items'):
        del db[name].settings['validator']['$jsonSchema']['properties']['synthetic_batch_id']
    result = audit(db)
    assert all('validator' in r['issues'] for r in result['collections']
               if r['name'] in ('orders', 'order_items'))
