"""Production behavior excludes synthetic batches and attribution opt-outs."""


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
