"""
Storage live migration mixed type domains sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Live_Storage_Migration
"""
from storage_migration_base import *  # flake8: noqa

ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.fixture(scope='module', autouse=True)
def inizialize_tests_params(request):
    """
    Determine whether to run plan on same storage type or on different types
    of storage
    """
    config.MIGRATE_SAME_TYPE = False


@pytest.mark.skipif((
    not any("iscsi" in sd for sd in config.SD_LIST) or
    not any("nfs" in sd for sd in config.SD_LIST)
), reason="No other storage type exist for HCI")
class TestCase10348(TestCase6004):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10348'


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
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True


class TestCase10338_powering_up(TestCase5994_powering_up):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


class TestCase10338_powering_off(TestCase5994_powering_off):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


class TestCase10338_wait_for_lunch(TestCase5994_wait_for_lunch):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


class TestCase10337(TestCase5993):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10337'


class TestCase10336(TestCase5992):
    """
    snapshots and move VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10336'


@bz({'1312909': {}})
class TestCase10335(TestCase5991):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )
    polarion_test_case = '10335'


class TestCase10333(TestCase5989):
    """
    suspended VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10333'


class TestCase10332_before_snapshot(TestCase5988_before_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


class TestCase10332_after_snapshot(TestCase5988_after_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


class TestCase10332_while_snapshot(TestCase5988_while_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


class TestCase10330(TestCase5986):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10330'


class TestCase10339(TestCase5995):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10339'


class TestCase10340_active_disk(TestCase5996_active_disk):
    """
    hot plug disk
    1) inactive disk
    2) active disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10340'


class TestCase10340_inactive_disk(TestCase5996_inactive_disk):
    """
    hot plug disk
    1) inactive disk
    2) active disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10340'


class TestCase10347_active_disk(TestCase6003_active_disk):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10347'


class TestCase10347_inactive_disk(TestCase6003_inactive_disk):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10347'


class TestCase10345(TestCase6001):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10345'


class TestCase10316(TestCase5972):
    """
    live migrate VM with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10316'


class TestCase10314(TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    polarion_test_case = '10314'


class TestCase10311(TestCase5967):
    """
    Space Reclamation after Deleting snapshot after- Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10311'


class TestCase10323(TestCase5979):
    """
    offline migration for disk attached to running VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10323'


class TestCase10320(TestCase5976):
    """
    Deactivate VM disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10320'


class TestCase10321_vm_migration(TestCase5977_vm_migration):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10321'


class TestCase10321_snapshot_creation(TestCase5977_snapshot_creation):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10321'


class TestCase10321_after_lsm(TestCase5977_after_lsm):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10321'


class TestCase10319_src_domain(TestCase5975_src_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10319'


class TestCase10319_dest_domain(TestCase5975_dest_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10319'


class TestCase10344(TestCase6000):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1106593
    __test__ = True
    polarion_test_case = '10344'


class TestCase10346(TestCase6002):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True
    polarion_test_case = '10346'


class TestCase10343_spm(TestCase5999_spm):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True
    polarion_test_case = '10343'


class TestCase10343_hsm(TestCase5999_hsm):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # Bugzilla history: 1210771
    __test__ = True
    polarion_test_case = '10343'


class TestCase10341_ha_vm(TestCase5997_ha_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10341'


class TestCase10341_regular_vm(TestCase5997_regular_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10341'


class TestCase10329(TestCase5985):
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


class TestCase10315(TestCase5971):
    """
    multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10315'


class TestCase10310_during_lsm(TestCase5966_during_lsm):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10310'


class TestCase10310_during_second_lsm(TestCase5966_during_second_lsm):
    """
    kill vdsm during second LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10310'


class TestCase10325(TestCase5981):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10325'


class TestCase10327_spm(TestCase5983_spm):
    """
    migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10327'


class TestCase10327_hsm(TestCase5983_hsm):
    """
    migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10327'


class TestCase10318(TestCase5974):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10318'
