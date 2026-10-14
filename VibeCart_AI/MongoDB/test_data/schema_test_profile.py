"""Additive v4 test-data profile; historical schema/migrations stay immutable."""
from copy import deepcopy
from schema_complete_v4 import SCHEMAS as BASE, INDEXES
from bootstrap_schema import obj, string, enum

MIGRATION = '20261005_05_synthetic_profile_v4'
SCHEMAS = deepcopy(BASE)
CHANGED = ('users', 'orders', 'order_items')
for name in CHANGED:
    SCHEMAS[name]['$jsonSchema']['properties']['synthetic_batch_id'] = string(100, minimum=1)
SCHEMAS['users']['$jsonSchema']['properties']['demographics'] = obj({
    'gender': enum('male', 'female', 'unspecified'),
    'birth_date': string(pattern=r'^\d{4}-\d{2}-\d{2}$'),
    'marital_status': enum('single', 'married', 'divorced', 'widowed', 'unspecified'),
    'as_of_date': string(pattern=r'^\d{4}-\d{2}-\d{2}$'),
})


def verify(db):
    """Read back every validator, index and document, including preserved sets."""
    if set(db.list_collection_names()) != set(SCHEMAS):
        raise ValueError('Unexpected collection set')
    result = {}
    for name, validator in SCHEMAS.items():
        options = db[name].options()
        if (options.get('validator') != validator or options.get('validationLevel') != 'strict'
                or options.get('validationAction') != 'error'):
            raise ValueError('Schema mismatch: ' + name)
        actual = {i['name']: i for i in db[name].list_indexes()}
        if set(actual) != {'_id_'} | {i.document['name'] for i in INDEXES[name]}:
            raise ValueError('Index set mismatch: ' + name)
        for model in INDEXES[name]:
            expected = model.document
            found = actual[expected['name']]
            for key, value in expected.items():
                if key == 'key' and 'text' in value.values():
                    if found.get('weights') != {'name': 1, 'description': 1}:
                        raise ValueError('Text index mismatch')
                elif found.get(key) != value:
                    raise ValueError('Index mismatch: ' + name)
            for key in ('unique', 'partialFilterExpression', 'expireAfterSeconds', 'sparse'):
                if found.get(key) != expected.get(key):
                    raise ValueError('Index option mismatch: ' + name)
        total = db[name].count_documents({})
        valid = db[name].count_documents(validator)
        if total != valid:
            raise ValueError('Invalid documents: ' + name)
        result[name] = {'count': total, 'conforming': valid, 'indexes': len(actual)}
    return result
