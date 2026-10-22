import copy
import pytest
from drive_backup_acl import DriveError
from drive_backup_daily import unchanged_remote


@pytest.mark.parametrize('change',['head','version','new','missing','incomplete'])
def test_changed_remote_state_requires_new_audit(change):
    before={'complete':True,'nodes':{'one':{'headRevisionId':'r1','version':'1','size':'10','md5Checksum':'a'}}}
    after=copy.deepcopy(before)
    assert unchanged_remote(before,after)
    if change=='head':after['nodes']['one']['headRevisionId']='r2'
    if change=='version':after['nodes']['one']['version']='2'
    if change=='new':after['nodes']['two']={}
    if change=='missing':after['nodes'].clear()
    if change=='incomplete':after['complete']=False
    with pytest.raises(DriveError,match='audit required'):unchanged_remote(before,after)
