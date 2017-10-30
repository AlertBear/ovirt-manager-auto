"""
Storage VM Floating Disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Hosted_Engine_Sanity
"""
import config
import pytest
import logging
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sds,
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.test_handler.settings import ART_CONFIG
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    add_disk, attach_disk, create_snapshot, create_vm, delete_disks,
    delete_disk,
)
from rhevmtests.storage.fixtures import remove_vm # noqa

from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    create_second_vm, initialize_disk_name,
)
from rhevmtests.storage.storage_get_device_name.fixtures import (
    create_vms_for_test, remove_vms,
)
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)
STORAGES = set([
    config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS,
    config.STORAGE_TYPE_FCP, config.STORAGE_TYPE_CEPH
])
NOT_GLUSTER = (
    config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
    config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] or
    config.STORAGE_TYPE_FCP in ART_CONFIG['RUN']['storages'] or
    config.STORAGE_TYPE_CEPH in ART_CONFIG['RUN']['storages']
)


@pytest.mark.usefixtures(
    initialize_disk_name.__name__,
    create_vms_for_test.__name__,
    delete_disk.__name__,
)
class TestCase11513(TestCase):
    """
    Test sharing disk
    Expected system: 2 vms with state down
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES

    polarion_test_case = '11513'

    @polarion("RHEVM3-11513")
    @tier1
    def test_shared(self):
        """Creates a shared disk and assign it to different vms
        """
        testflow.step("Creating sharable raw disk %s", self.disk_name)
        assert ll_disks.addDisk(
            True, alias=self.disk_name, provisioned_size=config.GB,
            interface=config.VIRTIO_SCSI, format=config.RAW_DISK,
            storagedomain=self.storage_domain,
            shareable=True, sparse=False
        )

        assert ll_disks.wait_for_disks_status(disks=[self.disk_name])
        testflow.step(
            "Attaching shared disk %s to vm %s",
            self.disk_name, self.vm_names[0]
        )
        assert ll_disks.attachDisk(True, self.disk_name, self.vm_names[0])
        assert ll_disks.wait_for_disks_status(disks=[self.disk_name])
        assert ll_vms.wait_for_vm_disk_active_status(
            self.vm_names[0], True, self.disk_name, sleep=1
        )
        # TODO: Extra validation ?

        testflow.step(
            "Attaching shared disk %s to vm %s", self.disk_name,
            self.vm_names[1]
        )
        assert ll_disks.attachDisk(True, self.disk_name, self.vm_names[1])
        assert ll_disks.wait_for_disks_status([self.disk_name])
        assert ll_vms.wait_for_vm_disk_active_status(
            self.vm_names[0], True, self.disk_name, sleep=1
        )
        assert ll_vms.wait_for_vm_disk_active_status(
            self.vm_names[1], True, self.disk_name, sleep=1
        )
        # TODO: Extra validation ?


@pytest.mark.usefixtures(
    initialize_disk_name.__name__,
    remove_vms.__name__,
    delete_disk.__name__,
)
class TestCase11624(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=834893
    scenario:
    * creates 4 VMs with nics but without disks
    * creates a shared disks
    * attaches the disk to the vms one at a time
    * runs all the vms on one host

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Bug_Coverage
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    polarion_test_case = '11624'
    disk_size = 1 * config.GB

    @classmethod
    @polarion("RHEVM3-11624")
    @tier2
    def test_several_vms_with_same_shared_disk_on_one_host_test(cls):
        """ tests if running a few VMs with the same shared disk on the same
            host works correctly
        """
        cls.vm_names = []
        for i in range(4):
            vm_name = storage_helpers.create_unique_object_name(
                cls.__name__, config.OBJECT_TYPE_VM
            )
            nic = "nic_%s" % i
            ll_vms.createVm(
                True, vm_name, vm_name, config.CLUSTER_NAME, nic=nic,
                placement_host=config.HOSTS[0], network=config.MGMT_BRIDGE,
                display_type=config.DISPLAY_TYPE, type=config.VM_TYPE,
                os_type=config.OS_TYPE
            )
            cls.vm_names.append(vm_name)
        storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage
        )[0]
        logger.info("Creating disk %s", cls.disk_name)
        assert ll_disks.addDisk(
            True, alias=cls.disk_name, shareable=True, bootable=False,
            provisioned_size=cls.disk_size, storagedomain=storage_domain,
            format=config.RAW_DISK, interface=config.VIRTIO_SCSI,
            sparse=False
        ), "failed to create disk %s" % cls.disk_name
        assert ll_disks.wait_for_disks_status(cls.disk_name)
        testflow.setup("Disk %s created successfully", cls.disk_name)

        for vm in cls.vm_names:
            assert ll_disks.attachDisk(True, cls.disk_name, vm, True), (
                "disk %s failed to attach to VM %s" % (cls.disk_name, vm)
            )

        ll_vms.start_vms(
            cls.vm_names, wait_for_status=config.VM_UP,
            max_workers=config.MAX_WORKERS, wait_for_ip=False
        )
        assert ll_vms.stop_vms_safely(cls.vm_names), "Failed to poweroff VMs"


@pytest.mark.usefixtures(delete_disks.__name__)
class TestCase5897(TestCase):
    """
    Create a shared disk with different formats
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    polarion_test_case = '5897'
    raw_disk = 'raw_shared_disk'
    cow_disk = 'cow_shared_disk'

    @polarion("RHEVM3-5897")
    @tier2
    def test_shared_disk_with_different_formats(self):
        """
        Update non sharable disk to be shareable
        """
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        assert ll_disks.addDisk(
            True, alias=self.raw_disk, provisioned_size=config.DISK_SIZE,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=False
        ), "Failed to create shared disk with format RAW"
        self.disks_to_remove.append(self.raw_disk)
        self.disks_to_remove.append(self.cow_disk)
        assert ll_disks.addDisk(
            False, alias=self.cow_disk, provisioned_size=config.DISK_SIZE,
            format=config.COW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=True
        ), "Succeeded to create shared disk with format COW"


@pytest.mark.usefixtures(
    add_disk.__name__,
    delete_disk.__name__
)
class TestCase16687(TestCase):
    """
    Move shared disk to GlusterFS storage domain
    """
    # Verify gluster storage available in yaml before running this test
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] and (
        'gluster' in str(config.STORAGE_NAME)
    )
    storages = set([config.STORAGE_TYPE_ISCSI])
    polarion_test_case = '16687'
    add_disk_params = {
        'format': config.RAW_DISK,
        'sparse': False,
        'shareable': True,
    }

    @polarion("RHEVM-16687")
    @tier3
    def test_move_shared_disk_to_gluster_domain(self):
        """
        Move shared disk to GlusterFS storage domain - should fail
        """
        gluster_storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, config.STORAGE_TYPE_GLUSTER
        )[0]
        assert not ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=gluster_storage_domain
        ), "Succeeded to move shared disk to Gluster storage domain"


@pytest.mark.usefixtures(delete_disks.__name__)
class TestCase16688(TestCase):
    """
    Create shared disk on GlusterFS storage domain
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    polarion_test_case = '16688'

    @polarion("RHEVM-16688")
    @tier3
    def test_create_shared_disk_on_gluster_domain(self):
        """
        Create shared disk on GlusterFS storage domain - should fail
        """
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        assert ll_disks.addDisk(
            False, alias=self.disk_name, provisioned_size=config.DISK_SIZE,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=False
        ), "Failed to create shared disk %s" % self.disk_name
        self.disks_to_remove.append(self.disk_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    delete_disk.__name__
)
class TestCase16685(TestCase):
    """
    Update disk to shareable
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    installation = False
    add_disk_params = {
        'format': config.RAW_DISK,
        'sparse': False,
    }

    @polarion("RHEVM-16685")
    @tier2
    def test_update_disk_to_shared(self):
        """
        Update non sharable disk to be shareable
        """
        assert ll_vms.updateDisk(
            True, vmName=self.vm_name, alias=self.disk_name, shareable=True
        ), "Failed to update disk sharable flag to 'True'"


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__
)
class TestCase16783(TestCase):
    """
    Update disk to shareable when the VM is powering up - Should fail
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    installation = False
    add_disk_params = {
        'format': config.RAW_DISK,
        'sparse': False,
    }

    @polarion("RHEVM-16783")
    @tier3
    def test_update_disk_to_shared_when_vm_is_powering_up(self):
        """
        Update non sharable disk to be shareable when the VM is powering up
        """
        assert ll_vms.startVm(True, self.vm_name)
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name, shareable=True
        ), (
            "Succeeded to update disk's %s sharable flag to 'True' when the "
            "VM is powering up" % self.disk_name
        )
        ll_vms.stop_vms_safely([self.vm_name])


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    create_snapshot.__name__
)
class TestCase16686(TestCase):
    """
    Update disk with snapshot to shareable
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    polarion_test_case = '16686'
    installation = False
    add_disk_params = {
        'format': config.RAW_DISK,
        'sparse': False,
    }

    @polarion("RHEVM-16686")
    @tier3
    def test_update_disk_with_snapshot_to_shared(self):
        """
        Update non sharable disk with snapshot to be shareable -> should fail
        """
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name, shareable=True
        ), ("Succeeded to update disk that is depend on snapshot to be "
            "shareable")


@pytest.mark.usefixtures(create_vm.__name__)
class TestCase16740(TestCase):
    """
    Attach non shared disk to second VM
    """
    __test__ = True
    polarion_test_case = '16740'
    installation = False

    @polarion("RHEVM-16740")
    @tier3
    def test_attach_non_shared_disk_to_second_vm(self):
        """
        Update non sharable disk to be shareable
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_disks.attachDisk(
            False, alias=vm_disk, vm_name=config.VM_NAME[0]
        ), "Succeeded to attach non shared disk to second VM %s" % (
            self.vm_name
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_second_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    delete_disk.__name__
)
class TestCase16781(TestCase):
    """
    Update sharable disk of 2 VMs to be non shareable - should fail
    """
    # Gluster doesn't support shareable disks
    __test__ = NOT_GLUSTER
    storages = STORAGES
    installation = False
    add_disk_params = {
        'shareable': True,
        'format': config.RAW_DISK,
        'sparse': False,
    }

    @polarion("RHEVM-16781")
    @tier2
    def test_update_shared_disk_of_2_vms_to_non_shared(self):
        """
        Update sharable disk of 2 VMs to be non shareable
        """
        assert ll_disks.attachDisk(
            True, alias=self.disk_name, vm_name=self.second_vm_name
        ), "Failed to attach shared disk to second VM %s" % (
            self.second_vm_name
        )
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name, shareable=False
        ), ("Succeeded to update disk that is shared between 2 VMs to be non "
            "shareable")
