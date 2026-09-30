import json
import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage
from app import create_app
from app.services.ai_workflows import (build_recommendation_graph, build_summary_graph,
    summary_metrics, operational_summary, CachedEmbeddings, claude_model)


class Embeddings:
    def embed_documents(self, texts):
        return [[1., 0.] if "瑜珈" in t else [0., 1.] for t in texts]

    def embed_query(self, text):
        return [1., 0.]


def products():
    return [{"_id": "yoga", "name": "瑜珈墊", "category": "瑜珈", "stock": 3, "rating": 4},
            {"_id": "weights", "name": "啞鈴", "category": "重訓", "stock": 3, "rating": 5},
            {"_id": "hidden", "name": "瑜珈", "stock": 1, "is_ai_recommendable": False},
            {"_id": "empty", "name": "瑜珈", "stock": 0}]


def test_real_langgraph_ranks_and_filters():
    graph = build_recommendation_graph(Embeddings())
    result = graph.invoke({"products": products(), "events": [], "query": "瑜珈"})
    assert result["source"] == "bge"
    assert [i["product"]["_id"] for i in result["items"]] == ["yoga", "weights"]


def test_embedding_failure_and_cold_start_fallback():
    def broken():
        raise RuntimeError("offline")
    graph = build_recommendation_graph(broken)
    for query in ("", "瑜珈"):
        result = graph.invoke({"products": products(), "events": [], "query": query})
        assert result["source"] == "rules" and len(result["items"]) == 2


def test_nonfinite_vector_falls_back():
    class Invalid(Embeddings):
        def embed_query(self, text):
            return [float("nan"), 0.]
    result = build_recommendation_graph(Invalid()).invoke({"products": products(), "events": [], "query": "test"})
    assert result["source"] == "rules"


def test_embedding_cache_invalidates_changed_text():
    class Counter(Embeddings):
        calls = 0
        def embed_documents(self, texts):
            self.calls += 1
            return super().embed_documents(texts)
    delegate = Counter()
    cache = CachedEmbeddings(delegate, capacity=2)
    cache.embed_documents(["瑜珈", "啞鈴"])
    cache.embed_documents(["瑜珈"])
    assert delegate.calls == 1
    cache.embed_documents(["新瑜珈墊"])
    assert delegate.calls == 2 and len(cache.cache) == 2


def test_summary_uses_allowlisted_metrics_and_real_langchain():
    insights = {"revenue": 100, "orders": 2, "avg_order": 50, "low_stock": [{"email": "private@example.test"}],
                "messages": ["規則式摘要"], "customer": "secret-name"}
    metrics = summary_metrics(insights)
    captured = []
    def respond(prompt):
        captured.append(prompt.to_string())
        return AIMessage(content="目前有兩筆有效訂單。")
    result = build_summary_graph(lambda: RunnableLambda(respond)).invoke({"metrics": metrics, "messages": insights["messages"], "source": "rules"})
    assert result["source"] == "claude" and result["messages"] == ["目前有兩筆有效訂單。"]
    assert "private@example.test" not in captured[0] and "secret-name" not in captured[0]
    assert "latest_100_orders" in captured[0]


def test_summary_failure_does_not_expose_exception():
    def failure():
        raise RuntimeError("provider-secret")
    result = build_summary_graph(failure).invoke({"metrics": {}, "messages": ["保留摘要"], "source": "rules"})
    assert result["source"] == "rules" and result["messages"] == ["保留摘要"]
    assert "provider-secret" not in json.dumps(result)


def test_disabled_summary_does_not_invoke_model():
    def fail():
        pytest.fail("Disabled model was invoked")
    app = create_app({"AI_SUMMARY_ENABLED": False, "CLAUDE_FACTORY": fail})
    with app.app_context():
        assert operational_summary({"messages": ["baseline"]})["source"] == "rules"


def test_anthropic_adapter_constructs_without_network():
    app = create_app({"ANTHROPIC_API_KEY": "offline-placeholder", "CLAUDE_MODEL": "test-model"})
    with app.app_context():
        model = claude_model()
        assert model.model == "test-model" and model.max_tokens == 600


def test_summary_cache_reuses_same_metrics_but_invalidates_changes():
    calls = []
    def response(prompt):
        calls.append(prompt)
        return AIMessage(content="彙總摘要")
    app = create_app({"AI_SUMMARY_ENABLED": True, "CLAUDE_FACTORY": lambda: RunnableLambda(response)})
    insights = {"revenue": 100, "orders": 2, "avg_order": 50, "low_stock": [], "messages": ["fallback"]}
    with app.app_context():
        assert operational_summary(insights)["source"] == "claude"
        operational_summary(insights)
        assert len(calls) == 1
        operational_summary({**insights, "revenue": 200})
        assert len(calls) == 2
