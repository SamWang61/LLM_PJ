"""CLI boundary tests with injected in-memory clients; no network connections."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import mongomock
import pytest
from bson import ObjectId
from bson.errors import InvalidId

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location('preference_cli_under_test', ROOT / 'scripts/rebuild_preference_scores.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)

from VibeCart_AI.services.preference_service import ScoreError


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / 'local-only.env'
    path.write_text('DATA_MODE=v4\nMONGO_URI=mongodb://127.0.0.1:1\nMONGO_DB=local_cli_scores\n', encoding='utf8')
    return path


def args(config, *identities, extra=()):
    result = ['--env-file', str(config)]
    for identity in identities:
        result += ['--user-id', str(identity)]
    return result + list(extra)


def seed(client, identity, active=True):
    db = client.local_cli_scores
    db.users.insert_one({'_id': identity, 'schema_version': 4,
                         'status': 'active' if active else 'inactive', 'is_active': active})
    if not db.system_configs.count_documents({}):
        db.system_configs.insert_one({'config_key': 'recommendation_policy', 'status': 'active', 'version': 1,
            'settings': {'weights': {'PURCHASE': 4, 'ADD_TO_CART': 3, 'SEARCH': 2, 'PRODUCT_VIEW': 1},
                         'half_life_days': {'PURCHASE': 365, 'ADD_TO_CART': 180, 'SEARCH': 90, 'PRODUCT_VIEW': 30},
                         'major_score_cap': 70, 'minor_score_cap': 30}})
    return db


def test_default_is_readonly_duplicate_members_are_deduplicated_and_output_is_summary(config_file, capsys):
    client = mongomock.MongoClient(tz_aware=True)
    uid = ObjectId()
    db = seed(client, uid)
    calls = []
    def factory(uri, **kwargs):
        calls.append((uri, kwargs))
        return client
    result = cli.main(args(config_file, uid, uid), client_factory=factory)
    assert result == {'mode': 'dry_run', 'members': 1, 'events_read': 0,
                      'events_scored': 0, 'excluded_purchase_events': 0}
    assert len(calls) == 1 and calls[0][0] == 'mongodb://127.0.0.1:1'
    assert db.user_preference_scores.count_documents({}) == 0
    output = capsys.readouterr().out
    assert [json.loads(row) for row in output.splitlines()] == [result]
    assert str(uid) not in output and 'mongodb://' not in output and 'snapshot' not in output


@pytest.mark.parametrize('extra', [('--max-events', '0'), ('--max-events', '100001'),
                                  ('--apply',), ('--apply', '--database-confirm', 'different_database')])
def test_invalid_bounds_or_apply_confirmation_never_connects(config_file, extra):
    def no_connection(*unused, **kwargs):
        pytest.fail('Invalid CLI request reached the client factory')
    with pytest.raises(ScoreError):
        cli.main(args(config_file, ObjectId(), extra=extra), client_factory=no_connection)


def test_more_than_100_member_arguments_fail_before_connection_even_if_duplicates(config_file):
    def no_connection(*unused, **kwargs):
        pytest.fail('Unbounded member batch reached the client factory')
    with pytest.raises(ScoreError):
        cli.main(args(config_file, *([ObjectId()] * 101)), client_factory=no_connection)


def test_invalid_member_fails_before_connection(config_file):
    def no_connection(*unused, **kwargs):
        pytest.fail('Malformed identity reached the client factory')
    with pytest.raises((ScoreError, InvalidId)):
        cli.main(args(config_file, 'not-an-object-id'), client_factory=no_connection)


def test_non_v4_configuration_never_connects(config_file):
    config_file.write_text('DATA_MODE=legacy\nMONGO_URI=mongodb://127.0.0.1:1\nMONGO_DB=local_cli_scores\n', encoding='utf8')
    def no_connection(*unused, **kwargs):
        pytest.fail('Unapproved connection mode reached the client factory')
    with pytest.raises(ScoreError):
        cli.main(args(config_file, ObjectId()), client_factory=no_connection)


def test_apply_uses_service_unique_index_guard(config_file):
    client = mongomock.MongoClient(tz_aware=True)
    uid = ObjectId()
    db = seed(client, uid)
    with pytest.raises(ScoreError):
        cli.main(args(config_file, uid, extra=('--apply', '--database-confirm', db.name)),
                 client_factory=lambda *unused, **kwargs: client)
    assert db.user_preference_scores.count_documents({}) == 0


def test_later_member_failure_preserves_prior_commit_and_only_prior_progress(config_file, capsys):
    client = mongomock.MongoClient(tz_aware=True)
    first, second = ObjectId(), ObjectId()
    db = seed(client, first)
    seed(client, second, active=False)
    db.user_preference_scores.create_index('user_id', unique=True)
    with pytest.raises(ScoreError):
        cli.main(args(config_file, first, second, extra=('--apply', '--database-confirm', db.name)),
                 client_factory=lambda *unused, **kwargs: client)
    assert db.user_preference_scores.count_documents({'user_id': first}) == 1
    assert db.user_preference_scores.count_documents({'user_id': second}) == 0
    progress = [json.loads(row) for row in capsys.readouterr().out.splitlines()]
    assert len(progress) == 1 and progress[0]['members'] == 1 and progress[0]['mode'] == 'apply'


def test_script_error_is_redacted_and_does_not_echo_input_or_config(config_file):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/rebuild_preference_scores.py'),
        *args(config_file, 'private-invalid-member')], text=True, capture_output=True, timeout=10)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report['status'] == 'failed' and report['error_type'] in {'ScoreError', 'InvalidId'}
    assert 'private-invalid-member' not in result.stdout and str(config_file) not in result.stdout
    assert 'mongodb://' not in result.stdout and not result.stderr


@pytest.mark.parametrize('private_options', [('--max-events', 'private-invalid-number'),
                                              ('--private-unknown-option=private-option-value',)])
def test_script_parser_errors_are_redacted_on_both_streams(config_file, private_options):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/rebuild_preference_scores.py'),
        *args(config_file, ObjectId(), extra=private_options)], text=True, capture_output=True, timeout=10)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report['status'] == 'failed' and report['error_type'] == 'ScoreError'
    assert not result.stderr
    for value in private_options:
        assert value not in result.stdout
    assert 'private-' not in result.stdout and str(config_file) not in result.stdout
