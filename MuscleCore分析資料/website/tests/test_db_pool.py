"""The worker shares transport only: failures and app/request isolation remain intact."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import MagicMock
import pytest
from pymongo.errors import ServerSelectionTimeoutError
from app import create_app
from app import db as module


def test_concurrent_requests_share_one_client_and_teardown_does_not_close(monkeypatch):
    factory = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(module, 'MongoClient', factory)
    app = create_app({'TESTING': True, 'MONGO_URI': 'mongodb://localhost:1', 'MONGO_DB': 'one'})
    assert factory.call_count == 0
    barrier = Barrier(8)
    def request(_):
        barrier.wait()
        with app.app_context():
            first = module.get_db()
            assert module.get_db() is first
            return first
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(request, range(8)))
    assert all(result is results[0] for result in results)
    assert factory.call_count == 1
    factory.return_value.close.assert_not_called()
    factory.return_value.admin.command.assert_not_called()
    assert factory.call_args.kwargs['socketTimeoutMS'] == 2500
    assert factory.call_args.kwargs['waitQueueTimeoutMS'] == 2500
    app.extensions['mongo_pool'].close()
    factory.return_value.close.assert_called_once()


def test_separate_apps_and_child_worker_never_reuse_parent_client(monkeypatch):
    clients = [MagicMock() for _ in range(3)]
    factory = MagicMock(side_effect=clients)
    monkeypatch.setattr(module, 'MongoClient', factory)
    apps = [create_app({'TESTING': True, 'MONGO_URI': 'mongodb://localhost:1'}) for _ in range(2)]
    for app in apps:
        with app.app_context(): module.get_db()
    parent = apps[0].extensions['mongo_pool']
    inherited_lock = parent.lock
    inherited_lock.acquire()
    try:
        # Same reset invoked by os.register_at_fork in Linux/Gunicorn children.
        module._after_fork()
        with apps[0].app_context(): module.get_db()
        assert parent.client is clients[2]
        assert parent.lock is not inherited_lock
        clients[0].close.assert_not_called()
        clients[1].close.assert_not_called()
    finally:
        inherited_lock.release()


def test_failed_initialization_can_retry_and_query_outage_recovers(monkeypatch):
    client = MagicMock()
    factory = MagicMock(side_effect=[ServerSelectionTimeoutError('offline'), client])
    monkeypatch.setattr(module, 'MongoClient', factory)
    app = create_app({'TESTING': True})
    with app.app_context(), pytest.raises(ServerSelectionTimeoutError): module.get_db()
    @app.get('/pool-probe')
    def probe():
        module.get_db().command('ping')
        return 'ok'
    client.__getitem__.return_value.command.side_effect = [ServerSelectionTimeoutError('offline'), {'ok': 1}]
    http = app.test_client()
    assert http.get('/pool-probe').status_code == 503
    assert http.get('/pool-probe').status_code == 200
    assert factory.call_count == 2
    client.close.assert_not_called()
