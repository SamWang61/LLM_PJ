"""Behavior scopes.

production_*: monitoring, attribution and recommendation performance. Excludes synthetic batches
and attribution opt-outs (for example demo checkouts).
personalization_*: what a member's own recommendations learn from. Excludes synthetic batches only,
so a real member's demo checkout still shapes their suggestions without counting as a conversion.
"""


def production_behavior_query(query=None):
    return {"$and": [query or {},
                     {"metadata.synthetic": {"$ne": True}},
                     {"metadata.synthetic_batch_id": {"$in": [None, ""]}},
                     {"metadata.exclude_from_attribution": {"$ne": True}}]}


def production_events(events):
    for event in events:
        metadata = event.get("metadata") or {}
        if (metadata.get("synthetic") is True
                or metadata.get("synthetic_batch_id") not in (None, "")
                or metadata.get("exclude_from_attribution") is True):
            continue
        yield event


def is_synthetic(metadata):
    return metadata.get("synthetic") is True or metadata.get("synthetic_batch_id") not in (None, "")


def personalization_behavior_query(query=None):
    return {"$and": [query or {},
                     {"metadata.synthetic": {"$ne": True}},
                     {"metadata.synthetic_batch_id": {"$in": [None, ""]}}]}


def personalization_events(events):
    for event in events:
        if not is_synthetic(event.get("metadata") or {}):
            yield event
