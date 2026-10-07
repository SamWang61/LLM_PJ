"""Current deployed contract. Historical migrations and overlay stay immutable."""
from test_data.schema_test_profile import SCHEMAS, INDEXES, MIGRATION
CONTRACT = 'v4-synthetic-profile-20261005'
MIGRATIONS = frozenset({
    '20260916_01_initial_schema_v2', '20260916_02_cart_state_events_v3',
    '20260918_03_schema_document_constraints', '20260918_04_complete_catalog_schema_v4',
    MIGRATION,
})
