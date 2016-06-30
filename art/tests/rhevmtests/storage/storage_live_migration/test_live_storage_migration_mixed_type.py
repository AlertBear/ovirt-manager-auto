"""
Storage live migration mixed type domains sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Live_Storage_Migration
"""
import config
import logging
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.settings import opts
import live_storage_migration_base as basePlan
from art.test_handler.tools import bz

logger = logging.getLogger(__name__)
ISCSI = config.STORAGE_TYPE_ISCSI


def setup_module():
    """
    Initialization of several parameters
    """
    config.TESTNAME = "LSM_mixed_type"
    logger.info("Setup module %s", config.TESTNAME)
    config.MIGRATE_SAME_TYPE = False
    global LOCAL_LUN, LOCAL_LUN_ADDRESS, LOCAL_LUN_TARGET
    LOCAL_LUN = config.UNUSED_LUNS[:]
    LOCAL_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES[:]
    LOCAL_LUN_TARGET = config.UNUSED_LUN_TARGETS[:]


@attr(tier=1)
class TestCase10348(basePlan.TestCase6004):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10348'


@attr(tier=2)
class TestCase5990(basePlan.TestCase5990):
    """
    vm in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase10338(basePlan.TestCase5994):
    """
    different vm status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Verify this case works properly. Previous comment state a
    # race condition could occur, in that case remove
    __test__ = False
    polarion_test_case = '10338'


@attr(tier=2)
@bz({'1311610': {}})
class TestCase10337(basePlan.TestCase5993):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: This has not been verified since the bz prevents to run it,
    # make sure it works properly
    __test__ = True
    polarion_test_case = '10337'


@attr(tier=2)
class TestCase10336(basePlan.TestCase5992):
    """
    snapshots and move vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10336'


@attr(tier=2)
class TestCase10335(basePlan.TestCase5991):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    polarion_test_case = '10335'


@attr(tier=2)
class TestCase10333(basePlan.TestCase5989):
    """
    suspended vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10333'


@attr(tier=2)
class TestCase10332(basePlan.TestCase5988):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


@attr(tier=2)
class TestCase10330(basePlan.TestCase5986):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case

    __test__ = False
    polarion_test_case = '10330'


@attr(tier=2)
class TestCase10339(basePlan.TestCase5995):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10339'


@attr(tier=2)
class TestCase10340(basePlan.TestCase5996):
    """
    hot plug disk
    1) inactive disk
    2) active disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10340'


@attr(tier=2)
class TestCase10347(basePlan.TestCase6003):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10347'


@attr(tier=2)
class TestCase10345(basePlan.TestCase6001):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10345'


@attr(tier=2)
class TestCase10316(basePlan.TestCase5972):
    """
    live migrate vm with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10316'


@attr(tier=2)
class TestCase10314(basePlan.TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    polarion_test_case = '10314'


@attr(tier=2)
class TestCase10313PowerOff(basePlan.TestCase5969PowerOff):
    # Bugzilla history: 1128582
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '10313'

    def turn_off_method(self):
        vms.stopVm(True, self.vm_name, 'false')


@attr(tier=2)
class TestCase10313Shutdown(basePlan.TestCase5969Shutdown):
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '10313'

    def turn_off_method(self):
        vms.shutdownVm(True, self.vm_name, 'false')


@attr(tier=2)
class TestCase10311(basePlan.TestCase5967):
    """
    Space Reclamation after Deleting snapshot after- Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration

    """
    __test__ = True
    polarion_test_case = '10311'


@attr(tier=2)
class TestCase10326(basePlan.TestCase5982):
    """
    merge snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10326'


@attr(tier=2)
class TestCase10323(basePlan.TestCase5979):
    """
    offline migration for disk attached to running vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10323'


@attr(tier=2)
class TestCase10320(basePlan.TestCase5976):
    """
    Deactivate vm disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = True
    polarion_test_case = '10320'


@attr(tier=2)
@bz({'1258219': {}})
class TestCase10321(basePlan.TestCase5977):
    """
    migrate a vm between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Add "Try to migrate the vm
    # during the LSM after the snapshot is created" case
    __test__ = True
    polarion_test_case = '10321'


@attr(tier=2)
class TestCase10319(basePlan.TestCase5975):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Needs 4 iscsi storage domains (only on block device)
    __test__ = False
    polarion_test_case = '10319'


@attr(tier=4)
class TestCase10344(basePlan.TestCase6000):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1106593
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '10344'


@attr(tier=4)
class TestCase10346(basePlan.TestCase6002):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    # TODO: tier4 jobs have not been verified
    __test__ = True
    polarion_test_case = '10346'


@attr(tier=4)
class TestCase10343(basePlan.TestCase5999):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    # TODO: tier4 jobs have not been verified
    __test__ = True
    polarion_test_case = '10343'


@attr(tier=4)
class TestCase10322(basePlan.TestCase5998):
    """
    Reboot host during live migration on HA vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    # TODO: tier4 jobs have not been verified
    __test__ = True
    polarion_test_case = '10322'


@attr(tier=4)
class TestCase10341(basePlan.TestCase5997):
    """
    kill vm's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '10341'


@attr(tier=2)
@bz({'1288862': {}})
class TestCase10329(basePlan.TestCase5985):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # TODO: this cases is disabled due to ticket RHEVM-2524
    # disks, wait for threshold feature

    jira = {'RHEVM-2524': None}
    __test__ = False
    polarion_test_case = '10329'


@attr(tier=2)
class TestCase10315(basePlan.TestCase5971):
    """
    multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10315'


@attr(tier=2)
class TestCase10324(basePlan.TestCase5980):
    """
    offline migration + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10324'


@attr(tier=4)
class TestCase10310(basePlan.TestCase5966):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '10310'


@attr(tier=2)
@bz({'11313744': {}})
class TestCase10325(basePlan.TestCase5981):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '10325'


@attr(tier=2)
class TestCase10327(basePlan.TestCase5983):
    """
    migrate multiple vm's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10327'


@attr(tier=4)
class TestCase10328(basePlan.TestCase5984):
    """
    connectivity issues to pool
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1106593, 1078095
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '10328'


@attr(tier=4)
class TestCase10318(basePlan.TestCase5974):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '10318'
