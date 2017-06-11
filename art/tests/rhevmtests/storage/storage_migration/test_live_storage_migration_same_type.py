"""
Storage live migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
from storage_migration_base import *  # flake8: noqa
from art.test_handler.tools import bz

ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.fixture(scope='module', autouse=True)
def inizialize_tests_params(request):
    """
    Determine whether to run plan on same storage type or on different types
    of storage
    """
    config.MIGRATE_SAME_TYPE = True


class TestCase6004(TestCase6004):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase21798(BaseTestCase21798):
    """
    Concurrent Live migration of multiple VM disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '21798'


class TestCase21907(BaseTestCase21907):
    """
    Concurrent Live migration of multiple VM disks during dd operation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '21907'


class TestCase5990(TestCase5990):
    """
    VM in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5994_powering_off(TestCase5994_powering_off):
    """
    different VM status
        https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    __test__ = True


class TestCase5994_powering_up(TestCase5994_powering_up):
    """
    different VM status
        https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    __test__ = True


class TestCase5994_wait_for_lunch(TestCase5994_wait_for_lunch):
    """
    different VM status
        https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    __test__ = True


class TestCase5993(TestCase5993):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5992(TestCase5992):
    """
    snapshots and move VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5991(TestCase5991):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )


class TestCase5989(TestCase5989):
    """
    suspended VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5988_before_snapshot(TestCase5988_before_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5988_after_snapshot(TestCase5988_after_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5988_while_snapshot(TestCase5988_while_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5986(TestCase5986):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5995(TestCase5995):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5996_active_disk(TestCase5996_active_disk):
    """
    hot plug disk
    1) inactive disk
    - create and run a VM
    - hot plug a floating disk and keep it inactive
    - move the disk images to a different domain
    2) active disk
    - create and run a VM
    - hot plug a disk and activate it
    - move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5996_inactive_disk(TestCase5996_inactive_disk):
    """
    hot plug disk
    1) inactive disk
    - create and run a VM
    - hot plug a floating disk and keep it inactive
    - move the disk images to a different domain
    2) active disk
    - create and run a VM
    - hot plug a disk and activate it
    - move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase6003_active_disk(TestCase6003_active_disk):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase6003_inactive_disk(TestCase6003_inactive_disk):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase6001(TestCase6001):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5972(TestCase5972):
    """
    live migrate VM with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5970(TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']


class TestCase5968(TestCase5968):
    """
    Auto-Shrink - Live Migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5967(TestCase5967):
    """
    Auto-Shrink - Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    """
    __test__ = True


class TestCase5979(TestCase5979):
    """
    offline migration for disk attached to running VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5976(TestCase5976):
    """
    Deactivate VM disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5977_after_lsm(TestCase5977_after_lsm):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5977_snapshot_creation(TestCase5977_snapshot_creation):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5977_vm_migration(TestCase5977_vm_migration):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5975_dest_domain(TestCase5975_dest_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5975_src_domain(TestCase5975_src_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase6000(TestCase6000):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1106593
    __test__ = True


class TestCase6002(TestCase6002):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


class TestCase5999_spm(TestCase5999_spm):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


class TestCase5999_hsm(TestCase5999_hsm):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True


class TestCase5997_ha_vm(TestCase5997_ha_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5997_regular_vm(TestCase5997_regular_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


@bz({'1288862': {}})
class TestCase5985(TestCase5985):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # TODO: this cases is disable due to ticket RHEVM-2524
    # disks
    jira = {'RHEVM-2524': None}
    __test__ = False


class TestCase5971(TestCase5971):
    """
    multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5966_during_lsm(TestCase5966_during_lsm):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5966_during_second_lsm(TestCase5966_during_second_lsm):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5981(TestCase5981):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5983_spm(TestCase5983_spm):
    """
    migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5983_hsm(TestCase5983_hsm):
    """
    migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase5974(TestCase5974):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
