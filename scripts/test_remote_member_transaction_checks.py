"""Deep checks must reject a production target or foreign fixtures before mutations."""
from unittest.mock import MagicMock
import pytest
import requests
from bson import ObjectId
import remote_member_transaction_checks as probe


def test_replay_copies_cookie_and_headers_without_mutating_original():
    original=requests.Session()
    original.headers['Authorization']='Bearer unused-test-token'
    original.cookies.set('__session','old-test-cookie')
    replay=probe.replay_session(original)
    original.cookies.set('__session','new-test-cookie')
    assert replay.cookies.get('__session')=='old-test-cookie'
    assert replay.headers['Authorization']=='Bearer unused-test-token'
    assert original.cookies.get('__session')=='new-test-cookie'


def test_wrong_database_is_rejected_before_collection_access():
    db=MagicMock();db.name='vibecart_ai'
    with pytest.raises(RuntimeError,match='database mismatch'):
        probe.scope(db,'marker',[ObjectId()],[ObjectId()],ObjectId())
    db.__getitem__.assert_not_called()


def test_foreign_fixture_is_rejected_before_insert_or_update():
    db=MagicMock();db.name='vibecart_acceptance_pr21'
    db.__getitem__.return_value.count_documents.return_value=0
    with pytest.raises(RuntimeError,match='fixture ownership'):
        probe.scope(db,'marker',[ObjectId()],[ObjectId()],ObjectId())
    db.users.insert_one.assert_not_called()
    db.users.update_one.assert_not_called()


def test_production_config_is_rejected_before_fixture_or_connection_use():
    db=MagicMock()
    config={'mongo_uri':'mongodb+srv://unused@vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai'}
    with pytest.raises(RuntimeError,match='scope mismatch'):
        probe.run(db,config,'marker',None,None,None,'unused','unused',[],[],{})
    db.__getitem__.assert_not_called()
