"""
3.5 Live merge
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Live_Merge
"""
from remove_snapshot_base import *  # flake8: noqa
import remove_snapshot_base as basePlan
from art.test_handler.tools import bz


class LiveMergeBaseClass(basePlan.BasicEnvironment):
    """
    Set live merge parameter to True
    """
    live_merge = True


class TestCase6038(LiveMergeBaseClass, basePlan.TestCase6038):
    """
    Basic live delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6038
    """
    __test__ = True
    test_case = '6038'


class TestCase6052(LiveMergeBaseClass, basePlan.TestCase6052):
    """
    Basic live delete and merge of snapshots with continuous I/O

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6052
    """
    __test__ = True
    test_case = '6052'


class TestCase16287(LiveMergeBaseClass, basePlan.TestCase16287):
    """
    Basic live delete and merge of a single snapshot's disk

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM/workitem?id=RHEVM3-16287
    """
    __test__ = True
    test_case = '16287'


class TestCase12215(LiveMergeBaseClass, basePlan.TestCase12215):
    """
    Deleting all snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-12215
    """
    __test__ = True
    test_case = '12215'


class TestCase6044(LiveMergeBaseClass, basePlan.TestCase6044):
    """
    Live delete and merge after deleting the base snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6044
    """
    __test__ = True
    test_case = '6044'


@bz({'1430358': {}})
class TestCase6045(LiveMergeBaseClass, basePlan.TestCase6045):
    """
    Live snapshot delete and merge with restart of vdsm

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6045
    """
    __test__ = True
    test_case = '6045'


class TestCase6043(LiveMergeBaseClass, basePlan.TestCase6043):
    """
    Live delete and merge after deleting the last created snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6043
    """
    __test__ = True
    test_case = '6043'


@bz({'1430358': {}})
class TestCase6046(LiveMergeBaseClass, basePlan.TestCase6046):
    """
    Live delete and merge of snapshot while stopping the engine

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6046
    """
    __test__ = True
    test_case = '6046'


class TestCase6048(LiveMergeBaseClass, basePlan.TestCase6048):
    """
    Consecutive delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6048
    """
    __test__ = True
    test_case = '6048'


class TestCase6050(LiveMergeBaseClass, basePlan.TestCase6050):
    """
    Delete a 2nd live snapshot during a delete and merge of another
    snapshot within the same VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6050
    """
    __test__ = True
    test_case = '6050'


class TestCase6057(LiveMergeBaseClass, basePlan.TestCase6057):
    """
    Live delete and merge of snapshot after disk Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6057
    """
    __test__ = True
    test_case = '6057'


class TestCase6058(LiveMergeBaseClass, basePlan.TestCase6058):
    """
    Live delete and merge of snapshot while crashing the VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6058
    """
    __test__ = True
    test_case = '6058'


class TestCase6062(LiveMergeBaseClass, basePlan.TestCase6062):
    """
    Live delete and merge of snapshot during Live Storage Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6062
    """
    __test__ = True
    test_case = '6062'


class TestCase12216(LiveMergeBaseClass, basePlan.TestCase12216):
    """
    Basic live merge after disk with snapshot is extended

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=12216
    """
    __test__ = True
    test_case = '12216'
