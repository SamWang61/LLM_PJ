from types import SimpleNamespace
import pytest
from provision_handover_demo import verify_public_role


class Browser:
    def __init__(self, role='customer', *, logout_ok=True, login_ok=True):
        self.role, self.logout_ok, self.login_ok = role, logout_ok, login_ok
        self.sessions = {'existing-device'}
        self.closed = False
        self.own = False
        self.logout_calls = 0

    def get(self, url, **kwargs):
        if url.endswith('/auth/login'):
            return SimpleNamespace(status_code=200, text='<input name="csrf_token" value="csrf">')
        if url == 'https://vibecart-llmai.web.app/':
            assert self.own
            return SimpleNamespace(status_code=200, text='<form action="/auth/logout"><input name="csrf_token" value="csrf"></form>')
        if url.endswith('/admin/'):
            # The real holder logs in after the probe. It must remain valid.
            self.sessions.add('concurrent-holder-device')
            return SimpleNamespace(status_code=200 if self.role == 'admin' else 302)
        assert url.endswith('/cart')
        return SimpleNamespace(status_code=200 if self.own else 302)

    def post(self, url, **kwargs):
        assert kwargs['data']['csrf_token'] == 'csrf'
        if url.endswith('/auth/login'):
            if self.login_ok:
                self.sessions.add('probe-device');self.own = True
            return SimpleNamespace(status_code=302 if self.login_ok else 200)
        assert url.endswith('/auth/logout')
        self.logout_calls += 1
        if self.logout_ok:
            self.sessions.discard('probe-device');self.own = False
        return SimpleNamespace(status_code=302 if self.logout_ok else 200)

    def close(self):
        self.closed = True


@pytest.mark.parametrize('role', ['customer', 'admin'])
def test_verification_logout_preserves_existing_and_concurrent_devices(role):
    browser = Browser(role)
    result = verify_public_role({'email':'demo@example.invalid','password':'fixture'}, role,
                                http_session_factory=lambda: browser)
    assert result['role_verified'] and result['own_device_logout_verified']
    assert browser.sessions == {'existing-device', 'concurrent-holder-device'}
    assert browser.closed and browser.logout_calls == 1


def test_logout_failure_cannot_be_reported_as_success():
    browser = Browser(logout_ok=False)
    with pytest.raises(RuntimeError, match='Own-device logout failed'):
        verify_public_role({'email':'demo@example.invalid','password':'fixture'}, 'customer',
                           http_session_factory=lambda: browser)
    assert browser.closed and 'concurrent-holder-device' in browser.sessions


def test_login_failure_closes_browser_without_revoking_any_device():
    browser = Browser(login_ok=False)
    with pytest.raises(RuntimeError, match='Demo login failed'):
        verify_public_role({'email':'demo@example.invalid','password':'fixture'}, 'customer',
                           http_session_factory=lambda: browser)
    assert browser.closed and browser.logout_calls == 0
    assert browser.sessions == {'existing-device'}
