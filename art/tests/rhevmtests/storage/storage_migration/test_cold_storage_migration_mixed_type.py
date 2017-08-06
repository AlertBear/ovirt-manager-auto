"""
Storage cold migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Cold_Move
"""
from storage_migration_base import *  # flake8: noqa
from cold_storage_migration_base import *  # flake8: noqa

ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.fixture(scope='module', autouse=True)
def inizialize_tests_params(request):
    """
    Determine whether to run plan on same storage type or on different types
    of storage and whether migration will be live or cold
    """
    config.MIGRATE_SAME_TYPE = False
    config.LIVE_MOVE = False


@pytest.mark.skipif(
    config.ISCSI_DOMAINS_KWARGS[0]['lun'] is None,
    reason="No other storage type exist for HCI"
)
class TestCase19001(TestCase6004):
    """
    Cold migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19649(TestCase5993):
    """
    Cold migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19651(TestCase5992):
    """
    Snapshots and move VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19019(TestCase5991):
    """
    Cold migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )


class TestCase19652_before_snapshot(TestCase5988_before_snapshot):
    """
    Create snapshot after cold storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19652_after_snapshot(TestCase5988_after_snapshot):
    """
    Create snapshot before cold storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19652_while_snapshot(TestCase5988_while_snapshot):
    """
    Create snapshot during cold storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19015(TestCase5986):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19023(TestCase5995):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19653_active_disk(TestCase5996_active_disk):
    """
    Plug active disk
    - Create a VM
    - Plug a disk and activate it
    - Move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19653_inactive_disk(TestCase5996_inactive_disk):
    """
    Plug inactive disk
    - create a VM
    - Plug a floating disk and keep it inactive
    - Move the disk images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19031_active_disk(TestCase6003_active_disk):
    """
    Attach active disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19031_inactive_disk(TestCase6003_inactive_disk):
    """
    Attach inactive disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19029(TestCase6001):
    """
    Cold migration to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19655(TestCase5972):
    """
    Cold migrate VM with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase18999(TestCase5970):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']


class TestCase19005(TestCase5976):
    """
    Deactivate a disk during Cold Move
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19004_dest_domain(TestCase5975_dest_domain):
    """
    Extend storage domain while cold migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19004_src_domain(TestCase5975_src_domain):
    """
    Extend storage domain while cold migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19014(TestCase5985):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # TODO: this cases is disable due to ticket RHEVM-2524
    # disks
    __test__ = False


class TestCase19000(TestCase5971):
    """
    Multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase18995(TestCase18995):
    """
    Restart vdsm on SPM before completing CopyImageGroupVolumesDataCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19059(TestCase19059):
    """
    Restart vdsm on SPM during CopyDataCommand on HSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19012(TestCase19012):
    """
    Cold Move multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19016(TestCase19016):
    """
    Domain upgraded to 4.1
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19035(TestCase19035):
    """
    Cold move a disk containing a snapshot, which has been extended
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19020(TestCase19020):
    """
    Cold move of VM with multiple snapshots
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19060_during_CopyImageGroupWithDataCmd(
    TestCase19060_during_CopyImageGroupWithDataCmd
):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19060_during_CloneImageGroupVolumesStructureCmd(
    TestCase19060_during_CloneImageGroupVolumesStructureCmd
):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19060_during_CreateVolumeContainerCommand(
    TestCase19060_during_CreateVolumeContainerCommand
):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19061(TestCase19061):
    """
    Restart Engine during 2 different move operations on SPM and HSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19095(TestCase19095):
    """
    Cold Move with disconnection of Network between Engine and
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19028(TestCase19028):
    """
    Storage connectivity issues between hosts and source domain
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True


class TestCase19007(TestCase19007):
    """
    Storage connectivity issues between hosts and source domain
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = True
