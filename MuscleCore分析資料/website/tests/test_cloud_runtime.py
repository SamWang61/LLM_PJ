"""Cloud session/preview/readiness contracts, without an Atlas connection."""
import pytest
from flask import g, session
from pymongo.errors import ServerSelectionTimeoutError

from cloud_runtime import create_cloud_app
from test_v4_routes import shop


@pytest.fixture
def cloud_env(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://vibecart-ai-free.odqe25w.mongodb.net/")
    monkeypatch.setenv("SECRET_KEY", "cloud-test-only-secret-key-32-chars")
    monkeypatch.setenv("CLOUD_PREVIEW_READ_ONLY", "true")


def test_cloud_rejects_default_secret_and_unapproved_cluster(cloud_env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "dev-only-secret")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_cloud_app()
    monkeypatch.setenv("SECRET_KEY", "cloud-test-only-secret-key-32-chars")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost/")
    with pytest.raises(RuntimeError, match="authorized"):
        create_cloud_app()


def test_preview_denies_all_write_and_account_routes(cloud_env):
    app = create_cloud_app()
    client = app.test_client()
    assert client.get("/health/live").json == {"status": "ok"}
    for path in ("/auth/login", "/auth/register", "/admin/", "/cart", "/checkout"):
        assert client.get(path).status_code == 403
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/").status_code == 403
    assert app.config["SESSION_COOKIE_NAME"] == "__session"
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["ENABLE_CHECKOUT"] is False
    assert client.get("/health/live").headers["Cache-Control"] == "private, no-store"


def test_preview_clears_member_identity_before_routes(cloud_env):
    app = create_cloud_app()

    @app.get("/session-check")
    def check():
        return {"member": session.get("user_id")}

    client = app.test_client()
    with client.session_transaction() as state:
        state.update(user_id="old-member", role="admin", name="old", event_session="old")
    result = client.get("/session-check")
    assert result.json == {"member": None}
    assert "__session=" in result.headers["Set-Cookie"]


def test_readiness_requires_catalog_and_hides_database_errors(cloud_env, shop, monkeypatch):
    _, _, db, *_ = shop
    app = create_cloud_app()

    @app.before_request
    def offline():
        g.db = db

    client = app.test_client()
    assert client.get("/health/ready").status_code == 200
    db.products.delete_many({})
    assert client.get("/health/ready").status_code == 503
    monkeypatch.setattr(db, "command", lambda *a: (_ for _ in ()).throw(ServerSelectionTimeoutError("private detail")))
    response = client.get("/health/ready")
    assert response.status_code == 503 and b"private detail" not in response.data


def test_cloud_refuses_ambiguous_preview_flag(cloud_env, monkeypatch):
    monkeypatch.setenv("CLOUD_PREVIEW_READ_ONLY", "yes")
    with pytest.raises(RuntimeError, match="true or false"):
        create_cloud_app()


def test_acceptance_database_requires_dedicated_service_and_explicit_mode(cloud_env, monkeypatch):
    monkeypatch.setenv("CLOUD_ACCEPTANCE_DB", "vibecart_acceptance_pr21")
    with pytest.raises(RuntimeError, match="isolated acceptance service"):
        create_cloud_app()
    monkeypatch.setenv("K_SERVICE", "vibecart-acceptance-pr21")
    monkeypatch.setenv("CLOUD_ACCEPTANCE_MODE", "true")
    with pytest.raises(RuntimeError, match="isolated acceptance service"):
        create_cloud_app()  # Still read-only; a write-enabled run needs its own approval.
    monkeypatch.setenv("CLOUD_PREVIEW_READ_ONLY", "false")
    app = create_cloud_app()
    assert app.config["MONGO_DB"] == "vibecart_acceptance_pr21"
    assert app.config["AI_RECOMMENDATIONS_ENABLED"] is False
    monkeypatch.setenv("CLOUD_ACCEPTANCE_DB", "vibecart_ai")
    with pytest.raises(RuntimeError, match="isolated acceptance service"):
        create_cloud_app()
    monkeypatch.setenv("CLOUD_ACCEPTANCE_DB", "vibecart_acceptance_pr21")
    monkeypatch.setenv("K_SERVICE", "vibecart-web")
    with pytest.raises(RuntimeError, match="isolated acceptance service"):
        create_cloud_app()


def test_acceptance_mode_without_database_fails_closed(cloud_env, monkeypatch):
    monkeypatch.setenv("CLOUD_ACCEPTANCE_MODE", "true")
    with pytest.raises(RuntimeError, match="requires CLOUD_ACCEPTANCE_DB"):
        create_cloud_app()


def test_preview_product_page_offers_browsing_without_disabled_account_flows(cloud_env, shop):
    _, _, db, _, pid, _ = shop
    app = create_cloud_app()

    @app.before_request
    def offline():
        g.db = db

    response = app.test_client().get(f"/product/{pid}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "會員與購物功能尚未開放" in html
    assert '<form' not in html and '/auth/login' not in html
    assert 'product-placeholder.svg' in html
    assert 'main-content' in html


@pytest.fixture
def no_ai_env(monkeypatch):
    for name in ("AI_RECOMMENDATIONS_ENABLED", "AI_SUMMARY_ENABLED", "AI_FREE_QUESTION_ENABLED",
                 "ANTHROPIC_API_KEY", "CLAUDE_MODEL", "BGE_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_cloud_ai_flags_default_off(cloud_env, no_ai_env):
    config = create_cloud_app().config
    assert not config["AI_RECOMMENDATIONS_ENABLED"] and not config["AI_SUMMARY_ENABLED"]
    assert not config["AI_FREE_QUESTION_ENABLED"] and config["ANTHROPIC_API_KEY"] == ""


def test_cloud_ai_flags_follow_environment(cloud_env, no_ai_env, monkeypatch):
    monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
    monkeypatch.setenv("AI_RECOMMENDATIONS_ENABLED", "TRUE")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-placeholder")
    monkeypatch.setenv("BGE_MODEL", "BAAI/bge-small-zh-v1.5")
    config = create_cloud_app().config
    assert config["AI_SUMMARY_ENABLED"] and config["AI_RECOMMENDATIONS_ENABLED"]
    assert not config["AI_FREE_QUESTION_ENABLED"]  # free questions need their own explicit flag
    assert config["CLAUDE_MODEL"] == "claude-test-model" and config["ANTHROPIC_API_KEY"] == "offline-placeholder"
    assert config["BGE_MODEL"] == "BAAI/bge-small-zh-v1.5"
    # Enabling AI must not relax the existing preview guard.
    assert create_cloud_app().test_client().get("/admin/").status_code == 403


@pytest.mark.parametrize("value", ["yes", "1", "on", "enabled"])
def test_cloud_refuses_ambiguous_ai_flag(cloud_env, no_ai_env, monkeypatch, value):
    monkeypatch.setenv("AI_SUMMARY_ENABLED", value)
    with pytest.raises(RuntimeError, match="AI_SUMMARY_ENABLED"):
        create_cloud_app()


def test_cloud_summary_without_key_falls_back_to_rules(cloud_env, no_ai_env, monkeypatch):
    from app.services.ai_workflows import operational_summary
    monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-test-model")
    app = create_cloud_app()
    with app.app_context():
        result = operational_summary({"revenue": 1, "orders": 1, "avg_order": 1, "low_stock": [], "messages": ["規則摘要"]})
    assert result["source"] == "rules" and result["messages"] == ["規則摘要"]
