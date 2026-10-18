import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import requests
from private_https_transport import PrivateHTTPSAdapter, HOST


def test_pipe_transport_keeps_cookie_and_redirect_semantics(monkeypatch):
    runner = MagicMock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps({
        'status': 302, 'headers': [['Location', '/cart'],
        ['Set-Cookie', 'fixture=opaque; Path=/; Secure; HttpOnly']],
        'body_base64': base64.b64encode(b'redirect').decode()})))
    monkeypatch.setattr('private_https_transport.subprocess.run', runner)
    session = requests.Session()
    session.mount('https://', PrivateHTTPSAdapter())
    response = session.get('https://' + HOST + '/auth/login', allow_redirects=False)
    assert response.status_code == 302 and response.headers['Location'] == '/cart'
    assert session.cookies.get('fixture') == 'opaque'
    request = session.prepare_request(requests.Request('GET', 'https://' + HOST + '/cart'))
    assert request.headers['Cookie'] == 'fixture=opaque'
    assert runner.call_count == 1


@pytest.mark.parametrize('url,verify', [
    ('https://example.invalid/cart', True), ('http://' + HOST + '/cart', True),
    ('https://' + HOST + ':444/cart', True), ('https://' + HOST + '/cart', False)])
def test_foreign_target_or_disabled_tls_is_rejected_before_process(monkeypatch, url, verify):
    runner = MagicMock()
    monkeypatch.setattr('private_https_transport.subprocess.run', runner)
    request = requests.Request('GET', url).prepare()
    with pytest.raises(requests.RequestException, match='scope mismatch'):
        PrivateHTTPSAdapter().send(request, verify=verify)
    runner.assert_not_called()


def test_post_transport_failure_is_not_retried_and_does_not_leak(monkeypatch):
    runner = MagicMock(return_value=SimpleNamespace(returncode=1, stdout='private-credential'))
    monkeypatch.setattr('private_https_transport.subprocess.run', runner)
    request = requests.Request('POST', 'https://' + HOST + '/checkout', json={'checkout_id': 'same'}).prepare()
    with pytest.raises(requests.ConnectionError) as error:
        PrivateHTTPSAdapter().send(request)
    assert str(error.value) == 'Private HTTPS pipe transport failed'
    assert runner.call_count == 1


def test_cookie_replay_preserves_the_selected_transport():
    from remote_member_transaction_checks import replay_session
    session = requests.Session()
    adapter = PrivateHTTPSAdapter()
    session.mount('https://', adapter)
    assert replay_session(session).get_adapter('https://' + HOST + '/cart') is adapter
