import pytest
from bs4 import BeautifulSoup
from remote_preview_ai_probe import admin_denied, cache_counts, validate
from types import SimpleNamespace


def config():
    return {"mongo_uri": "mongodb+srv://sam_pr21_acceptance_20261017:placeholder@vibecart-ai-free.odqe25w.mongodb.net/vibecart_acceptance_pr21",
            "service_url": "https://main20ee-ai---vibecart-acceptance-pr21-example.a.run.app",
            "revision": "vibecart-acceptance-pr21-main20ee-1640",
            "image": "example/image@sha256:" + "a" * 64, "expect_claude": False}


@pytest.mark.parametrize("key,value", [
    ("mongo_uri", "mongodb+srv://sam_pr21_acceptance_20261017:placeholder@vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai"),
    ("service_url", "https://vibecart-web-example.a.run.app"),
    ("service_url", "https://main20ee-ai---vibecart-web-example.a.run.app"),
    ("service_url", "https://user:pass@main20ee-ai---vibecart-acceptance-pr21-example.a.run.app"),
    ("revision", "vibecart-web-main20ee-1640"),
    ("image", "example/image:latest"),
    ("expect_claude", "false"),
    ("expect_claude", 0),
])
def test_wrong_targets_and_ambiguous_expectations_rejected_before_connection(key, value):
    value_config = config()
    value_config[key] = value
    with pytest.raises(RuntimeError):
        validate(value_config)


def test_guarded_private_tag_is_accepted():
    validate(config())


@pytest.mark.parametrize("status,location", [(403, None), (302, "/"), (303, "/")])
def test_role_guard_accepts_existing_home_redirect_and_forbidden(status, location):
    admin_denied(SimpleNamespace(status_code=status, headers={"Location": location}))


@pytest.mark.parametrize("status,location", [(200, None), (302, "/admin/"), (302, "https://example.invalid/")])
def test_role_guard_does_not_accept_admin_content_or_other_redirects(status, location):
    with pytest.raises(RuntimeError):
        admin_denied(SimpleNamespace(status_code=status, headers={"Location": location}))


def test_missing_model_message_cannot_be_accepted_as_real_scores():
    with pytest.raises(RuntimeError):
        cache_counts(BeautifulSoup('<div class="model-warning">model missing</div>', "html.parser"))


def test_nonfinite_display_score_cannot_pass_measurement():
    soup = BeautifulSoup('<div class="similar-row"><b class="score-value">nan</b></div><p>快取命中 2/2</p>', "html.parser")
    with pytest.raises(RuntimeError):
        cache_counts(soup)
