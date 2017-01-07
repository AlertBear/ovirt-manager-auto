"""
4.1 Cold merge
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Cold_Merge
"""
from art.test_handler.tools import bz
import remove_snapshot_base as basePlan
from rhevmtests.storage.fixtures import (
    create_vm, prepare_disks_with_fs_for_vm, delete_disks,
    wait_for_disks_and_snapshots, remove_vm
)  # flake8: noqa
from rhevmtests.storage.storage_remove_snapshots.fixtures import (
    initialize_params,
)  # flake8: noqa
from art.unittest_lib import attr


@bz({'1410428': {}})
class ColdMergeBaseClass(basePlan.BasicEnvironment):
    """
    Set live merge parameter to False
    """
    live_merge = False


@attr(tier=1)
class TestCase18894(ColdMergeBaseClass, basePlan.TestCase6038):
    """
    Basic offline delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6038
    """
    __test__ = True
    test_case = '18894'


@attr(tier=2)
class TestCase18923(ColdMergeBaseClass, basePlan.TestCase16287):
    """
    Basic offline delete and merge of a single snapshot's disk

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM/workitem?id=RHEVM3-16287
    """
    __test__ = True
    test_case = '18923'


@attr(tier=3)
class TestCase18912(ColdMergeBaseClass, basePlan.TestCase12215):
    """
    Deleting all snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-12215
    """
    __test__ = True
    test_case = '18912'


@attr(tier=3)
class TestCase18900(ColdMergeBaseClass, basePlan.TestCase6044):
    """
    Offline delete and merge after deleting the base snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6044
    """
    __test__ = True
    test_case = '18900'


@attr(tier=4)
class TestCase18901(ColdMergeBaseClass, basePlan.TestCase6045):
    """
    Offline snapshot delete and merge with restart of vdsm

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6045
    """
    __test__ = True
    test_case = '18901'


@attr(tier=3)
class TestCase18899(ColdMergeBaseClass, basePlan.TestCase6043):
    """
    Offline delete and merge after deleting the last created snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6043
    """
    __test__ = True
    test_case = '18899'


@attr(tier=4)
class TestCase18902(ColdMergeBaseClass, basePlan.TestCase6046):
    """
    Offline delete and merge of snapshot while stopping the engine

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6046
    """
    __test__ = True
    test_case = '18902'


@attr(tier=3)
class TestCase18904(ColdMergeBaseClass, basePlan.TestCase6048):
    """
    Consecutive delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6048
    """
    __test__ = True
    test_case = '18904'


@attr(tier=3)
class TestCase18906(ColdMergeBaseClass, basePlan.TestCase6050):
    """
    Delete a 2nd offline snapshot during a delete and merge of another
    snapshot within the same VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6050
    """
    __test__ = True
    test_case = '18906'


@attr(tier=2)
class TestCase18920(ColdMergeBaseClass, basePlan.TestCase12216):
    """
    Basic offline merge after disk with snapshot is extended

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=12216
    """
    __test__ = True
    test_case = '18920'
