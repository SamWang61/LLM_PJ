"""Local vs Cloud comparison built only from measured calls in this process.

Measurements come from record_ai_call (ai_workflows): they reset when the server restarts and
are per worker process. Nothing here is a sample or default value; unmeasured cells stay None.
"""
from decimal import Decimal
from statistics import median
from flask import current_app

RECENT = 10
LOCAL_KINDS = {"similar_products"}
CLOUD_KINDS = {"insight", "summary"}


def price_per_mtok(name):
    raw = str(current_app.config.get(name) or "").strip()
    try:
        value = Decimal(raw)
    except ArithmeticError:
        return None
    return value if value >= 0 else None


def summarize(calls, kinds):
    picked = [c for c in calls if c.get("kind") in kinds][-RECENT:]
    if not picked:
        return {"samples": 0, "median_ms": None, "last_at": None}
    return {"samples": len(picked), "median_ms": median(c["latency_ms"] for c in picked), "last_at": picked[-1]["at"]}


def cloud_cost(calls):
    """Average tokens per call and, only when both unit prices are configured, an estimated USD cost."""
    picked = [c for c in calls if c.get("kind") in CLOUD_KINDS][-RECENT:]
    measured = [c for c in picked if c.get("input_tokens") is not None and c.get("output_tokens") is not None]
    if not measured:
        return {"samples": 0, "avg_input": None, "avg_output": None, "usd": None, "priced": False}
    avg_in = Decimal(sum(c["input_tokens"] for c in measured)) / len(measured)
    avg_out = Decimal(sum(c["output_tokens"] for c in measured)) / len(measured)
    price_in, price_out = price_per_mtok("CLAUDE_INPUT_USD_PER_MTOK"), price_per_mtok("CLAUDE_OUTPUT_USD_PER_MTOK")
    usd = None
    if price_in is not None and price_out is not None:
        usd = ((avg_in * price_in + avg_out * price_out) / Decimal(1_000_000)).quantize(Decimal("0.00001"))
    return {"samples": len(measured), "avg_input": round(avg_in), "avg_output": round(avg_out), "usd": usd, "priced": usd is not None}


def comparison():
    calls = list(current_app.extensions.get("ai_calls", []))
    return {"local": summarize(calls, LOCAL_KINDS), "cloud": summarize(calls, CLOUD_KINDS), "cost": cloud_cost(calls),
            "recent_calls": list(reversed(calls[-20:])), "window": RECENT}
