"""
Storage live migration mixed type domains sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Live_Storage_Migration
"""
import config
import pytest
from art.unittest_lib import attr
from art.test_handler.settings import opts
import live_storage_migration_base as basePlan
from art.test_handler.tools import bz

from rhevmtests.storage.fixtures import (
    update_vm_disk, create_snapshot, delete_disks, deactivate_domain,
    add_disk_permutations, remove_templates, remove_vms, restart_vdsmd,
    unblock_connectivity_storage_domain_teardown, wait_for_disks_and_snapshots,
    initialize_storage_domains, initialize_variables_block_domain, create_vm,
    start_vm, create_second_vm, poweroff_vm
)
from rhevmtests.storage.storage_live_migration.fixtures import (
    initialize_params, initialize_disk_args, add_disk, attach_disk_to_vm,
    initialize_domain_to_deactivate, create_disks_for_vm, create_templates,
    prepare_disks_for_vm, initialize_vm_and_template_names,
    create_vms_from_templates, add_two_storage_domains
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.fixture(scope='module', autouse=True)
def inizialize_tests_params(request):
    """
    Determine whether to run plan on same storage type or on different types
    of storage
    """
    config.MIGRATE_SAME_TYPE = False
    config.TESTNAME = "LSM_mixed_type"


@attr(tier=1)
class TestCase10348(basePlan.TestCase6004):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10348'


@attr(tier=3)
class TestCase5990(basePlan.TestCase5990):
    """
    VM in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True


@attr(tier=2)
class TestCase10338_powering_up(basePlan.TestCase5994_powering_up):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


@attr(tier=2)
class TestCase10338_powering_off(basePlan.TestCase5994_powering_off):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


@attr(tier=2)
class TestCase10338_wait_for_lunch(basePlan.TestCase5994_wait_for_lunch):
    """
    different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10338'


@attr(tier=2)
class TestCase10337(basePlan.TestCase5993):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10337'


@attr(tier=3)
class TestCase10336(basePlan.TestCase5992):
    """
    snapshots and move VM
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


@attr(tier=3)
class TestCase10333(basePlan.TestCase5989):
    """
    suspended VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10333'


@attr(tier=3)
class TestCase10332_before_snapshot(basePlan.TestCase5988_before_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


@attr(tier=3)
class TestCase10332_after_snapshot(basePlan.TestCase5988_after_snapshot):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10332'


@attr(tier=3)
class TestCase10332_while_snapshot(basePlan.TestCase5988_while_snapshot):
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
    __test__ = True
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


@attr(tier=3)
class TestCase10340_active_disk(basePlan.TestCase5996_active_disk):
    """
    hot plug disk
    1) inactive disk
    2) active disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10340'


@attr(tier=3)
class TestCase10340_inactive_disk(basePlan.TestCase5996_inactive_disk):
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
class TestCase10347_active_disk(basePlan.TestCase6003_active_disk):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10347'


@attr(tier=2)
class TestCase10347_inactive_disk(basePlan.TestCase6003_inactive_disk):
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
    live migrate VM with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10316'


@attr(tier=3)
class TestCase10314(basePlan.TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    polarion_test_case = '10314'


@attr(tier=3)
class TestCase10311(basePlan.TestCase5967):
    """
    Space Reclamation after Deleting snapshot after- Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10311'


@attr(tier=3)
class TestCase10323(basePlan.TestCase5979):
    """
    offline migration for disk attached to running VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10323'


@attr(tier=3)
class TestCase10320(basePlan.TestCase5976):
    """
    Deactivate VM disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10320'


@attr(tier=3)
class TestCase10321_vm_migration(basePlan.TestCase5977_vm_migration):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Add "Try to migrate the VM
    # during the LSM after the snapshot is created" case
    __test__ = True
    polarion_test_case = '10321'


@attr(tier=3)
class TestCase10321_snapshot_creation(basePlan.TestCase5977_snapshot_creation):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Add "Try to migrate the VM
    # during the LSM after the snapshot is created" case
    __test__ = True
    polarion_test_case = '10321'


@attr(tier=3)
class TestCase10321_after_lsm(basePlan.TestCase5977_after_lsm):
    """
    migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: Add "Try to migrate the VM
    # during the LSM after the snapshot is created" case
    __test__ = True
    polarion_test_case = '10321'


@attr(tier=2)
class TestCase10319_src_domain(basePlan.TestCase5975_src_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10319'


@attr(tier=2)
class TestCase10319_dest_domain(basePlan.TestCase5975_dest_domain):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
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
    __test__ = True
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
class TestCase10343_spm(basePlan.TestCase5999_spm):
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
class TestCase10343_hsm(basePlan.TestCase5999_hsm):
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
class TestCase10341_ha_vm(basePlan.TestCase5997_ha_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10341'


@attr(tier=4)
class TestCase10341_regular_vm(basePlan.TestCase5997_regular_vm):
    """
    kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
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


@attr(tier=4)
class TestCase10310(basePlan.TestCase5966):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = True
    polarion_test_case = '10310'


@attr(tier=4)
class TestCase10325(basePlan.TestCase5981):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10325'


@attr(tier=2)
class TestCase10327_spm(basePlan.TestCase5983_spm):
    """
    migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '10327'


@attr(tier=2)
class TestCase10327_hsm(basePlan.TestCase5983_hsm):
    """
    migrate multiple VM's disks
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
    __test__ = True
    polarion_test_case = '10328'


@attr(tier=4)
class TestCase10318(basePlan.TestCase5974):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_6_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = True
    polarion_test_case = '10318'
