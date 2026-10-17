"""A stale snapshot must fail even when its own files are internally consistent."""
import pytest
from audit_delivery_source import require_stable_head


@pytest.mark.parametrize("before,after", [("old", "new"), ("new", "new"), ("old", "old")])
def test_rejects_any_mismatch_with_audited_head(before, after):
    audited = "old" if before != after else "other"
    with pytest.raises(RuntimeError, match="Remote main moved"):
        require_stable_head(audited, before, after)


def test_accepts_only_the_same_observed_head():
    require_stable_head("same", "same", "same")
