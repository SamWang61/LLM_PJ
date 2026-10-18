"""Scope and disclosure checks for the localhost-only N06 tool."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts import run_local_checkout_fault_matrix as matrix


@pytest.mark.parametrize('name', ['vibecart_ai', 'vibecart_acceptance_pr21',
                                'ren_n06_foreign_case', 'ren_n06_own_case/other'])
def test_cleanup_refuses_foreign_databases(name):
    with pytest.raises(RuntimeError, match='Foreign cleanup database'):
        matrix.owned_database(name, 'own')


@pytest.mark.parametrize('relative', ['..', '../node0', 'node0/nested', 'other'])
def test_cleanup_refuses_paths_outside_exact_owned_node(tmp_path, relative):
    with pytest.raises(RuntimeError, match='Foreign process data'):
        matrix.owned_data_path(tmp_path/relative, tmp_path)


def test_only_generated_database_and_direct_node_paths_are_accepted(tmp_path):
    matrix.owned_database('ren_n06_own_network_timeout', 'own')
    matrix.owned_data_path(tmp_path/'node0', tmp_path)


def test_command_observer_never_retains_documents_or_credentials():
    trace = matrix.Trace()
    trace.started(SimpleNamespace(command_name='insert', command={
        'insert':'users', 'documents':[{'password_hash':'must-not-be-retained',
                                     'member_session':'private-session-token'}],
        'txnNumber':8, 'startTransaction':True}))
    text = json.dumps(trace.rows)
    assert 'must-not-be-retained' not in text and 'private-session-token' not in text
    assert 'documents' not in text and trace.rows[0]['txn']==8


def test_invalid_binary_is_rejected_before_creating_cluster_directory(tmp_path):
    fake = tmp_path/'other.exe'
    fake.write_bytes(b'not a binary')
    with patch.object(matrix.tempfile, 'mkdtemp') as create:
        with pytest.raises(RuntimeError, match='mongod binary required'):
            matrix.Cluster(fake)
        create.assert_not_called()


def test_failed_process_start_still_removes_its_precreated_data_directory(tmp_path):
    binary = tmp_path/'mongod'
    binary.write_bytes(b'fixture binary; process creation is mocked')
    run = tmp_path/'run'
    run.mkdir()
    with patch.object(matrix.tempfile, 'mkdtemp', return_value=str(run)):
        cluster = matrix.Cluster(binary)
    with patch.object(matrix.subprocess, 'Popen', side_effect=OSError('startup failed')):
        with pytest.raises(OSError, match='startup failed'):
            cluster.start()
    assert (run/'node0').exists()
    cluster.close()
    assert cluster.cleaned and not (run/'node0').exists()
