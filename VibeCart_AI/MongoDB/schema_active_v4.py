"""Current deployed contract. Historical migrations and overlay stay immutable."""
from copy import deepcopy
from test_data.schema_test_profile import SCHEMAS as BASE_SCHEMAS, INDEXES as BASE_INDEXES, MIGRATION
from auth_session_schema import VALIDATOR, INDEXES as SESSION_INDEXES, MIGRATION as SESSION_MIGRATION
SCHEMAS = deepcopy(BASE_SCHEMAS)
INDEXES = deepcopy(BASE_INDEXES)
SCHEMAS['auth_sessions'] = VALIDATOR
INDEXES['auth_sessions'] = SESSION_INDEXES
CONTRACT = 'v4-member-device-sessions-20261014'
MIGRATIONS = frozenset({
    '20260916_01_initial_schema_v2', '20260916_02_cart_state_events_v3',
    '20260918_03_schema_document_constraints', '20260918_04_complete_catalog_schema_v4',
    MIGRATION,
    SESSION_MIGRATION,
})
