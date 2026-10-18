import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from bson import ObjectId
sys.path.insert(0,str(Path(__file__).parent))
from remote_dual_role_acceptance_probe import cleanup

@pytest.mark.parametrize('name,marker,ids',[
    ('vibecart_ai','sam-dual-role-owned',[ObjectId() for _ in range(6)]),
    ('vibecart_acceptance_pr21','unowned',[ObjectId() for _ in range(6)]),
    ('vibecart_acceptance_pr21','sam-dual-role-owned',[ObjectId()]),
    ('vibecart_acceptance_pr21','sam-dual-role-owned',['untrusted']*6),
])
def test_cleanup_rejects_wrong_database_or_unregistered_users(name,marker,ids):
    with pytest.raises(RuntimeError,match='scope'):cleanup(SimpleNamespace(name=name),marker,ids)

def test_cleanup_requires_every_dependent_readback():
    db=MagicMock();db.name='vibecart_acceptance_pr21';collections={x:MagicMock() for x in ['users','auth_sessions','behavior_events']}
    db.__getitem__.side_effect=collections.__getitem__
    for c in collections.values():c.count_documents.return_value=0;c.delete_many.return_value.deleted_count=1
    ids=[ObjectId() for _ in range(6)]
    assert cleanup(db,'sam-dual-role-owned',ids)['verified']
    collections['auth_sessions'].count_documents.return_value=1
    assert not cleanup(db,'sam-dual-role-owned',ids)['verified']
    collections['auth_sessions'].count_documents.side_effect=RuntimeError('readback unavailable')
    assert not cleanup(db,'sam-dual-role-owned',ids)['verified']
