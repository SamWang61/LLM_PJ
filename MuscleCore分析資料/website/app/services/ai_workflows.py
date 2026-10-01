"""LangGraph orchestration with LangChain model adapters and offline fallbacks.

No tools, database writes, or customer records are exposed to the language model.
Model factories are injectable so graph execution can be tested without network.
"""
import hashlib
import json
import logging
import math
from collections import OrderedDict
from threading import Lock
from time import monotonic
from typing import TypedDict
from flask import current_app
from .recommendation import recommend_products

logger = logging.getLogger(__name__)


class RecommendationState(TypedDict, total=False):
    products: list
    events: list
    query: str
    items: list
    source: str


class SummaryState(TypedDict, total=False):
    metrics: dict
    messages: list
    source: str


class CachedEmbeddings:
    """Bounded process-local product embedding cache, invalidated by text content."""
    def __init__(self, delegate, capacity=512):
        self.delegate, self.capacity = delegate, capacity
        self.cache = OrderedDict()
        self.lock = Lock()

    def embed_documents(self, texts):
        with self.lock:
            missing = list(dict.fromkeys(t for t in texts if t not in self.cache))
            if missing:
                vectors = self.delegate.embed_documents(missing)
                if len(vectors) != len(missing):
                    raise ValueError("Embedding count mismatch")
                self.cache.update(zip(missing, vectors))
            result = [self.cache[t] for t in texts]
            for text in texts:
                self.cache.move_to_end(text)
            while len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            return result

    def embed_query(self, text):
        return self.delegate.embed_query("为这个句子生成表示以用于检索相关文章：" + text)


def bge_embeddings():
    if "bge_embeddings" not in current_app.extensions:
        from langchain_huggingface import HuggingFaceEmbeddings
        current_app.extensions["bge_embeddings"] = CachedEmbeddings(HuggingFaceEmbeddings(
            model_name=current_app.config["BGE_MODEL"],
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True}))
    return current_app.extensions["bge_embeddings"]


def cosine(a, b):
    if not a or len(a) != len(b) or not all(math.isfinite(x) for x in [*a, *b]):
        raise ValueError("Invalid embedding")
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    if not denominator:
        raise ValueError("Zero embedding")
    return sum(x*y for x, y in zip(a, b)) / denominator


def product_text(product):
    return " ".join(str(product.get(k, "")) for k in ("name", "category", "summary", "description", "product_tags"))[:2000]


def build_recommendation_graph(embeddings):
    from langgraph.graph import StateGraph, START, END

    def baseline(state):
        products = [p for p in state["products"] if p.get("is_ai_recommendable", True) and p.get("stock", 0) > 0]
        events = [{**e, "event_type": {"PRODUCT_VIEW": "view", "ADD_TO_CART": "cart", "PURCHASE": "purchase"}.get(e.get("event_type"), e.get("event_type"))} for e in state["events"]]
        return {"products": products, "items": recommend_products(products, events), "source": "rules"}

    def rank(state):
        if not state["products"]:
            return {}
        query = state["query"].strip()
        if not query:
            by_id = {str(p["_id"]): p for p in state["products"]}
            recent = [by_id[str(e["product_id"])] for e in state["events"] if str(e.get("product_id")) in by_id][:5]
            query = " ".join(product_text(p) for p in recent)[:1000]
        if not query:
            return {}
        try:
            model = embeddings() if callable(embeddings) else embeddings
            vectors = model.embed_documents([product_text(p) for p in state["products"]])
            if len(vectors) != len(state["products"]):
                raise ValueError("Embedding count mismatch")
            vector = model.embed_query(query)
            ranked = sorted(zip(state["products"], vectors), key=lambda pair: cosine(vector, pair[1]), reverse=True)
            return {"items": [{"product": p, "reason": "與你的搜尋或近期關注商品語意相近", "score": round(cosine(vector, v), 4)}
                              for p, v in ranked[:4]], "source": "bge"}
        except Exception:
            logger.warning("BGE unavailable; using rule recommendations")
            return {}

    graph = StateGraph(RecommendationState)
    graph.add_node("eligible_and_baseline", baseline)
    graph.add_node("bge_rank", rank)
    graph.add_edge(START, "eligible_and_baseline")
    graph.add_edge("eligible_and_baseline", "bge_rank")
    graph.add_edge("bge_rank", END)
    return graph.compile()


def storefront_recommendations(products, events, query=""):
    if current_app.config["AI_RECOMMENDATIONS_ENABLED"]:
        try:
            graph = build_recommendation_graph(current_app.config.get("EMBEDDINGS_FACTORY", bge_embeddings))
            return graph.invoke({"products": products, "events": events, "query": query})
        except ImportError:
            logger.warning("Install AI requirements to enable LangGraph")
    eligible = [p for p in products if p.get("is_ai_recommendable", True) and p.get("stock", 0) > 0]
    normalized = [{**e, "event_type": {"PRODUCT_VIEW": "view", "ADD_TO_CART": "cart", "PURCHASE": "purchase"}.get(e.get("event_type"), e.get("event_type"))} for e in events]
    return {"items": recommend_products(eligible, normalized), "source": "rules"}


def summary_metrics(insights):
    """Allowlist: no names, emails, IDs, free-text product content or raw orders."""
    return {"currency": "TWD", "scope": insights.get("scope_key", "latest_100_orders"),
            "start": insights.get("start", ""), "end": insights.get("end", ""),
            "timezone": "Asia/Taipei", "demo": insights.get("demo", "all"),
            "data_mode": insights.get("mode", "v4"),
            "revenue": str(insights["revenue"]),
            "paid_orders": insights["orders"], "average_order_value": str(insights["avg_order"]),
            "low_stock_skus": insights.get("low_stock_count", len(insights["low_stock"]))}


def claude_model():
    from langchain_anthropic import ChatAnthropic
    if not current_app.config["ANTHROPIC_API_KEY"] or not current_app.config["CLAUDE_MODEL"]:
        raise ValueError("Claude configuration missing")
    return ChatAnthropic(model=current_app.config["CLAUDE_MODEL"], api_key=current_app.config["ANTHROPIC_API_KEY"],
                         timeout=20, max_retries=1, max_tokens=600)


def build_summary_graph(model_factory):
    from langgraph.graph import StateGraph, START, END
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    def summarize(state):
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是電商營運分析助理。僅依提供的彙總數據，以繁體中文提出三點簡短摘要。"
                 "scope=latest_100_orders 表示最近100筆；date_range 表示台北時間 start 至 end 含結束日。"
                 "須說明 demo 的示範訂單篩選。data_mode=legacy 的有效訂單並非確認付款。"
                 "低庫存是目前狀態，並非過去區間。不能宣稱全站營收或推論成長趨勢。"
                 "不得捏造商品、因果或數字；資料不足須說明。建議供人工評估，不執行任何操作。"),
                ("human", "營運統計：{metrics}")])
            chain = prompt | model_factory() | StrOutputParser()
            text = chain.invoke({"metrics": json.dumps(state["metrics"], ensure_ascii=False)})
            if not text.strip() or len(text) > 6000:
                raise ValueError("Invalid summary")
            return {"messages": [text], "source": "claude"}
        except Exception:
            logger.warning("Claude unavailable; using rule summary")
            return {"source": "rules"}

    graph = StateGraph(SummaryState)
    graph.add_node("claude_summary", summarize)
    graph.add_edge(START, "claude_summary")
    graph.add_edge("claude_summary", END)
    return graph.compile()


def operational_summary(insights):
    fallback = {"messages": insights["messages"], "source": "rules"}
    if not current_app.config["AI_SUMMARY_ENABLED"]:
        return fallback
    try:
        metrics = summary_metrics(insights)
        fingerprint = hashlib.sha256(json.dumps([current_app.config["CLAUDE_MODEL"], metrics], sort_keys=True).encode()).hexdigest()
        cache = current_app.extensions.setdefault("summary_cache", {"lock": Lock()})
        with cache["lock"]:
            if cache.get("key") == fingerprint and monotonic() < cache.get("expires", 0):
                return cache["result"]
            graph = build_summary_graph(current_app.config.get("CLAUDE_FACTORY", claude_model))
            result = graph.invoke({"metrics": metrics, **fallback})
            # Keep one bounded entry; brief failure cooldown avoids repeated API errors.
            cache.update(key=fingerprint, result=result, expires=monotonic() + (300 if result["source"] == "claude" else 30))
            return result
    except ImportError:
        logger.warning("Install AI requirements to enable LangGraph")
        return fallback
