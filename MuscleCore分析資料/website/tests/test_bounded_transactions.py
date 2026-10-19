"""Contract checks for outcomes that must not duplicate checkout writes."""
import pytest
from pymongo.errors import AutoReconnect, OperationFailure
from app.services.sku_gateway import CartService


class Session:
    def __init__(self, commit_errors=()):
        self.in_transaction = False
        self.started = self.aborted = self.commits = 0
        self.commit_errors = list(commit_errors)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def start_transaction(self, **_):
        self.in_transaction = True
        self.started += 1

    def abort_transaction(self):
        self.in_transaction = False
        self.aborted += 1

    def commit_transaction(self):
        self.commits += 1
        if self.commit_errors:
            raise self.commit_errors.pop(0)
        self.in_transaction = False


class Client:
    def __init__(self, session):
        self.session = session

    def start_session(self):
        return self.session


def service(session):
    return CartService(type('Database', (), {'client': Client(session)})())


def test_labeled_socket_loss_never_replays_transaction_callback():
    session = Session()
    failure = AutoReconnect('connection lost after a transactional write')
    failure._add_error_label('TransientTransactionError')
    calls = []

    def callback(_):
        calls.append(1)
        raise failure

    with pytest.raises(AutoReconnect):
        service(session)._run(callback)
    assert len(calls) == session.started == session.aborted == 1
    assert session.commits == 0


def test_unknown_commit_retries_same_transaction_without_replaying_callback():
    unknown = OperationFailure('acknowledgement lost', 91,
        {'errorLabels': ['UnknownTransactionCommitResult']})
    session = Session([unknown])
    calls = []

    def callback(_):
        calls.append(1)
        return 'one-order'

    assert service(session)._run(callback) == 'one-order'
    assert len(calls) == session.started == 1
    assert session.commits == 2 and session.aborted == 0
