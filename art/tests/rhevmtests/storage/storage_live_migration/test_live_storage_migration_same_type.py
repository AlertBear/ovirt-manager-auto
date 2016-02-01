"""
Storage live migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
import config
import logging
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.settings import opts
import live_storage_migration_base as basePlan
from art.test_handler.tools import bz  # pylint: disable=E0611

logger = logging.getLogger(__name__)
ISCSI = config.STORAGE_TYPE_ISCSI


def setup_module():
    """
    Initialization of several parameters
    """
    config.TESTNAME = "LSM_same_type"
    logger.info("Setup module %s", config.TESTNAME)
    config.MIGRATE_SAME_TYPE = True
    global LOCAL_LUN, LOCAL_LUN_ADDRESS, LOCAL_LUN_TARGET
    LOCAL_LUN = config.UNUSED_LUNS[:]
    LOCAL_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES[:]
    LOCAL_LUN_TARGET = config.UNUSED_LUN_TARGETS[:]


@attr(tier=1)
class TestCase6004(basePlan.TestCase6004):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5990(basePlan.TestCase5990):
    """
    vm in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5994(basePlan.TestCase5994):
    """
    different vm status
        https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    # TODO: Verify this case works properly. Previous comment state a
    # race condition could occur, in that case remove
    __test__ = False


@attr(tier=2)
class TestCase5993(basePlan.TestCase5993):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: This has not been verified since there is a bz that prevents it
    # from being run. Add the bz and test this once more
    __test__ = False


@attr(tier=2)
class TestCase5992(basePlan.TestCase5992):
    """
    snapshots and move vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5991(basePlan.TestCase5991):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )


@attr(tier=2)
class TestCase5989(basePlan.TestCase5989):
    """
    suspended vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5988(basePlan.TestCase5988):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5986(basePlan.TestCase5986):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False


@attr(tier=2)
class TestCase5955(basePlan.TestCase5955):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5996(basePlan.TestCase5996):
    """
    hot plug disk
    1) inactive disk
    - create and run a vm
    - hot plug a floating disk and keep it inactive
    - move the disk images to a different domain
    2) active disk
    - create and run a vm
    - hot plug a disk and activate it
    - move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase6003(basePlan.TestCase6003):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase6001(basePlan.TestCase6001):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5972(basePlan.TestCase5972):
    """
    live migrate vm with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5970(basePlan.TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = ISCSI in opts['storages']


@attr(tier=2)
class TestCase5969(basePlan.TestCase5969):
    """
    Power off/Shutdown of vm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False


class TestCase5969PowerOff(basePlan.TestCase5969PowerOff):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        vms.stopVm(True, self.vm_name, 'false')


class TestCase5969Shutdown(basePlan.TestCase5969Shutdown):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        vms.shutdownVm(True, self.vm_name, 'false')


@attr(tier=2)
class TestCase5968(basePlan.TestCase5968):
    """
    Auto-Shrink - Live Migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5967(basePlan.TestCase5967):
    """
    Auto-Shrink - Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    __test__ = True


@attr(tier=2)
class TestCase5982(basePlan.TestCase5982):
    """
    merge snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5979(basePlan.TestCase5979):
    """
    offline migration for disk attached to running vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5976(basePlan.TestCase5976):
    """
    Deactivate vm disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False


@attr(tier=2)
@bz({'1258219': {}})
class TestCase5977(basePlan.TestCase5977):
    """
    migrate a vm between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5975(basePlan.TestCase5975):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Needs 4 iscsi storage domains (only on block device)
    __test__ = False


@attr(tier=4)
class TestCase6000(basePlan.TestCase6000):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1106593
    # TODO: tier3 jobs have not been verified
    __test__ = False


@attr(tier=4)
class TestCase6002(basePlan.TestCase6002):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


@attr(tier=4)
class TestCase5999(basePlan.TestCase5999):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


@attr(tier=4)
class TestCase5998(basePlan.TestCase5998):
    """
    reboot host during live migration on HA vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


@attr(tier=4)
class TestCase5997(basePlan.TestCase5997):
    """
    kill vm's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False


@attr(tier=2)
class TestCase5985(basePlan.TestCase5985):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # disks
    __test__ = False


@attr(tier=2)
class TestCase5971(basePlan.TestCase5971):
    """
    multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase5980(basePlan.TestCase5980):
    """
    offline migration + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=4)
class TestCase5966(basePlan.TestCase5966):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False


@attr(tier=2)
class TestCase5981(basePlan.TestCase5981):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False


@attr(tier=2)
class TestCase5983(basePlan.TestCase5983):
    """
    migrate multiple vm's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=4)
class TestCase5984(basePlan.TestCase5984):
    """
    connectivity issues to pool
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    - https://bugzilla.redhat.com/show_bug.cgi?id=1078095
    """
    # Bugzilla history: 1106593
    # TODO: tier3 jobs have not been verified
    __test__ = False


@attr(tier=4)
class TestCase5974(basePlan.TestCase5974):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
