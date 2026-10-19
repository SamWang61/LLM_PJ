"""Failed container startup must remain a failure and retain diagnostics."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('cleanup_fails', [False, True])
def test_exited_container_is_diagnosed_and_cleanup_is_attempted(tmp_path, monkeypatch, cleanup_fails):
    path = Path(__file__).with_name('run_transaction_acceptance.py')
    spec = importlib.util.spec_from_file_location('transaction_harness_startup', path)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    calls = []
    container = {}

    def fake_docker(*args):
        calls.append(args)
        if args[0] == 'run':
            container['name'] = args[args.index('--name') + 1]
            return 'owned-container-id'
        if args[0] == 'port':
            return '127.0.0.1:49152'
        if args[0] == 'exec':
            raise subprocess.CalledProcessError(1, ['docker', *args])
        if args[0] == 'inspect':
            return json.dumps([{'Name': '/' + container['name'], 'State': {
                'Status': 'exited', 'ExitCode': 137, 'OOMKilled': True, 'Error': ''}}])
        if args[0] == 'logs':
            return 'local startup failure evidence'
        if args[0] == 'rm':
            if cleanup_fails:
                raise subprocess.CalledProcessError(1, ['docker', *args])
            return container['name']
        raise AssertionError(args)

    report = tmp_path / 'report.json'
    monkeypatch.setattr(harness, 'docker', fake_docker)
    monkeypatch.setattr(harness.time, 'sleep', lambda _: None)
    monkeypatch.setattr(sys, 'argv', ['test', '--report', str(report),
                                    '--junit', str(tmp_path / 'junit.xml')])
    assert harness.main() == 1
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['status'] == ('cleanup-failed' if cleanup_fails else 'failed')
    assert result['container_removed'] is (not cleanup_fails)
    assert result['container_state']['ExitCode'] == 137
    assert result['container_state']['OOMKilled'] is True
    assert result['container_logs_tail'] == 'local startup failure evidence'
    assert '--rm' not in calls[0]
    assert ('rm', '-f', container['name']) in calls
