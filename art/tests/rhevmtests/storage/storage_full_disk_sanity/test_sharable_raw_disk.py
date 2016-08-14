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
    jobs as ll_jobs,
    storagedomains as ll_sds,
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.unittest_lib import StorageTest as TestCase, attr, testflow
from rhevmtests.storage import helpers as storage_helpers
from art.test_handler import exceptions
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)


@attr(tier=1)
class TestCase11513(TestCase):
    """
    Test sharing disk
    Expected system: 2 vms with state down
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_ISCSI in opts['storages']
        or config.STORAGE_TYPE_CEPH in opts['storages']
    )
    storages = set(
        [config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS,
         config.STORAGE_TYPE_CEPH]
    )

    polarion_test_case = '11513'
    disk_name = "shareableDisk"

    def setUp(self):
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        for vm_prefix in [config.VM1_NAME, config.VM2_NAME]:
            vm_name = vm_prefix % self.storage
            vm_args = config.create_vm_args.copy()
            vm_args['storageDomainName'] = self.storage_domain
            vm_args['vmName'] = vm_name
            vm_args['installation'] = False
            vm_args['start'] = 'true'
            if not storage_helpers.create_vm_or_clone(**vm_args):
                raise exceptions.VMException(
                    "Failed to create vm %s" % vm_name
                )
        self.vm_1 = config.VM1_NAME % self.storage
        self.vm_2 = config.VM2_NAME % self.storage
        if not ll_vms.waitForVmsStates(True, [self.vm_1, self.vm_2]):
            raise exceptions.VMException(
                "VMs %s are not in state 'OK'" % [self.vm_1, self.vm_2]
            )

    @polarion("RHEVM3-11513")
    def test_shared(self):
        """Creates a shared disk and assign it to different vms
        """
        testflow.step("Creating sharable raw disk %s", self.disk_name)
        self.assertTrue(
            ll_disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                interface=config.VIRTIO_SCSI, format=config.RAW_DISK,
                storagedomain=self.storage_domain,
                shareable=True, sparse=False
            )
        )

        self.assertTrue(ll_disks.wait_for_disks_status(disks=[self.disk_name]))
        testflow.step(
            "Attaching shared disk %s to vm %s", self.disk_name, self.vm_1
        )
        self.assertTrue(ll_disks.attachDisk(True, self.disk_name, self.vm_1))
        self.assertTrue(ll_disks.wait_for_disks_status(disks=[self.disk_name]))
        self.assertTrue(
            ll_vms.wait_for_vm_disk_active_status(
                self.vm_1, True, self.disk_name, sleep=1
            )
        )
        # TODO: Extra validation ?

        testflow.step(
            "Attaching shared disk %s to vm %s", self.disk_name, self.vm_2
        )
        self.assertTrue(ll_disks.attachDisk(True, self.disk_name, self.vm_2))
        self.assertTrue(ll_disks.wait_for_disks_status([self.disk_name]))
        self.assertTrue(
            ll_vms.wait_for_vm_disk_active_status(
                self.vm_1, True, self.disk_name, sleep=1
            )
        )
        self.assertTrue(
            ll_vms.wait_for_vm_disk_active_status(
                self.vm_2, True, self.disk_name, sleep=1
            )
        )
        # TODO: Extra validation ?

    def tearDown(self):
        """
        Remove vms
        """
        if not ll_vms.safely_remove_vms([self.vm_1, self.vm_2]):
            logger.error(
                "Failed to power off and remove vms %s", [self.vm_1, self.vm_2]
            )
            TestCase.test_failed = True
        if not ll_disks.deleteDisk(True, self.disk_name):
            logger.error(
                "Failed to delete disk %s", self.disk_name
            )
            TestCase.test_failed = True
        TestCase.teardown_exception()


@attr(tier=2)
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
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '11624'
    disk_name = None
    disk_size = 1 * config.GB

    @polarion("RHEVM3-11624")
    def test_several_vms_with_same_shared_disk_on_one_host_test(self):
        """ tests if running a few VMs with the same shared disk on the same
            host works correctly
        """
        self.vm_names = []
        for i in range(4):
            vm_name = "vm_%s_%s" % (self.polarion_test_case, i)
            nic = "nic_%s" % i
            ll_vms.createVm(
                True, vm_name, vm_name, config.CLUSTER_NAME, nic=nic,
                placement_host=config.HOSTS[0], network=config.MGMT_BRIDGE,
                display_type=config.DISPLAY_TYPE, type=config.VM_TYPE,
                os_type=config.OS_TYPE
            )
            self.vm_names.append(vm_name)
        storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.disk_name = 'disk_%s' % self.polarion_test_case
        logger.info("Creating disk %s", self.disk_name)
        assert ll_disks.addDisk(
            True, alias=self.disk_name, shareable=True, bootable=False,
            provisioned_size=self.disk_size, storagedomain=storage_domain,
            format=config.RAW_DISK, interface=config.VIRTIO_SCSI,
            sparse=False
        )
        assert ll_disks.wait_for_disks_status(self.disk_name)
        logger.info("Disk %s created successfully", self.disk_name)

        for vm in self.vm_names:
            assert ll_disks.attachDisk(True, self.disk_name, vm, True)

        ll_vms.start_vms(
            self.vm_names, max_workers=config.MAX_WORKERS, wait_for_ip=False
        )

    def tearDown(self):
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error(
                "Failed to power off and remove vms %s", self.vm_names
            )
            TestCase.test_failed = True
        if self.disk_name is not None:
            if not ll_disks.deleteDisk(True, self.disk_name):
                logger.error("Failed to delete disk %s", self.disk_name)
                TestCase.test_failed = True
        TestCase.teardown_exception()


class BaseClass(TestCase):
    """
    Base class for various cases
    """
    # Gluster doesn't support shareable disks
    __test__ = False
    disk_size = 1 * config.GB

    @pytest.fixture(scope='function')
    def baseClass_initializer(self, request):
        request.addfinalizer(self.finalizer)
        self.initializer()

    def initializer(self):

        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['installation'] = False
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm_name
            )
        if not ll_vms.addDisk(
            True, self.vm_name, provisioned_size=self.disk_size,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO_SCSI, format=config.RAW_DISK,
            shareable=False, sparse=False
        ):
            raise exceptions.DiskException("Failed to create disk for test")
        ll_disks.wait_for_disks_status([self.disk_name])

    def finalizer(self):
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error(
                "Failed to power off and remove vm %s", self.vm_name
            )
            TestCase.test_failed = True
        if ll_disks.checkDiskExists(True, self.disk_name) and not (
            ll_disks.deleteDisk(True, self.disk_name)
        ):
            logger.error("Failed to delete disk %s", self.disk_name)
            TestCase.test_failed = True
        TestCase.teardown_exception()


@attr(tier=2)
class TestCase5897(TestCase):
    """
    Create a shared disk with different formats
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages'] or
        config.STORAGE_TYPE_FCP in opts['storages'] or
        config.STORAGE_TYPE_CEPH in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '5897'
    disk_size = 1 * config.GB
    raw_disk = 'raw_shared_disk'
    cow_disk = 'cow_shared_disk'
    cow_disk_added = True

    @pytest.fixture(scope='function')
    def case5897_initializer(self, request):
        def case5897_finalizer():
            ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])
            if not ll_disks.deleteDisk(True, self.raw_disk):
                logger.error("Failed to delete disk %s", self.raw_disk)
                TestCase.test_failed = True
            if self.cow_disk_added and not ll_disks.deleteDisk(
                True, self.cow_disk
            ):
                logger.error("Failed to delete disk %s", self.cow_disk)
                TestCase.test_failed = True
            TestCase.teardown_exception()
        request.addfinalizer(case5897_finalizer)
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

    @polarion("RHEVM3-5897")
    @pytest.mark.usefixtures("case5897_initializer")
    def test_shared_disk_with_different_formats(self):
        """
        Update non sharable disk to be shareable
        """
        self.assertTrue(ll_disks.addDisk(
            True, alias=self.raw_disk, provisioned_size=self.disk_size,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=False
        ), "Failed to create shared disk with format RAW")
        self.assertTrue(ll_disks.addDisk(
            False, alias=self.cow_disk, provisioned_size=self.disk_size,
            format=config.COW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=True
        ), "Succeeded to create shared disk with format COW")
        self.cow_disk_added = False


@attr(tier=2)
class TestCase16687(TestCase):
    """
    Move shared disk to GlusterFS storage domain
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '16687'
    disk_size = 1 * config.GB

    @pytest.fixture(scope='function')
    def case16687_initializer(self, request):
        def case16687_finalizer():
            if not ll_disks.deleteDisk(True, self.disk_name):
                logger.error("Failed to delete disk %s", self.disk_name)
                TestCase.test_failed = True
            TestCase.teardown_exception()
        request.addfinalizer(case16687_finalizer)
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        self.assertTrue(ll_disks.addDisk(
            True, alias=self.disk_name, provisioned_size=self.disk_size,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=False
        ), "Failed to create shared disk %s" % self.disk_name)
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])

    @polarion("RHEVM3-16687")
    @pytest.mark.usefixtures("case16687_initializer")
    def test_move_shared_disk_to_gluster_domain(self):
        """
        Move shared disk to GlusterFS storage domain - should fail
        """
        gluster_storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, config.STORAGE_TYPE_GLUSTER
        )[0]
        self.assertFalse(ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=gluster_storage_domain
        ), "Succeeded to move shared disk to Gluster storage domain")


@attr(tier=2)
class TestCase16688(TestCase):
    """
    Create shared disk on GlusterFS storage domain
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    polarion_test_case = '16688'
    disk_size = 1 * config.GB
    created = True

    @pytest.fixture(scope='function')
    def case16688_initializer(self, request):
        def case16688_finalizer():
            if self.created and not ll_disks.deleteDisk(True, self.disk_name):
                logger.error("Failed to delete disk %s", self.disk_name)
                TestCase.test_failed = True
            TestCase.teardown_exception()
        request.addfinalizer(case16688_finalizer)
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )

    @polarion("RHEVM3-16688")
    @pytest.mark.usefixtures("case16688_initializer")
    def test_create_shared_disk_on_gluster_domain(self):
        """
        Create shared disk on GlusterFS storage domain - should fail
        """
        self.assertTrue(ll_disks.addDisk(
            False, alias=self.disk_name, provisioned_size=self.disk_size,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            shareable=True, sparse=False
        ), "Failed to create shared disk %s" % self.disk_name)
        self.created = False


@attr(tier=2)
class TestCase16685(BaseClass):
    """
    Update disk to shareable
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages'] or
        config.STORAGE_TYPE_FCP in opts['storages'] or
        config.STORAGE_TYPE_CEPH in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '16685'

    @polarion("RHEVM3-16685")
    @pytest.mark.usefixtures("baseClass_initializer")
    def test_update_disk_to_shared(self):
        """
        Update non sharable disk to be shareable
        """
        self.assertTrue(ll_vms.updateDisk(
            True, vmName=self.vm_name, alias=self.disk_name, shareable=True
        ), "Failed to update disk sharable flag to 'True'")


@attr(tier=2)
class TestCase16686(BaseClass):
    """
    Update disk with snapshot to shareable
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages'] or
        config.STORAGE_TYPE_FCP in opts['storages'] or
        config.STORAGE_TYPE_CEPH in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '16686'
    snapshot = 'snapshot_%s' % polarion_test_case

    def case16686_finalizer(self):
        self.finalizer()
        TestCase.teardown_exception()

    @pytest.fixture(scope='function')
    def case16686_initializer(self, request):
        request.addfinalizer(self.case16686_finalizer)
        self.initializer()

    @polarion("RHEVM3-16686")
    @pytest.mark.usefixtures("case16686_initializer")
    def test_update_disk_with_snapshot_to_shared(self):
        """
        Update non sharable disk with snapshot to be shareable -> should fail
        """
        ll_vms.addSnapshot(True, self.vm_name, self.snapshot)
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
        self.assertTrue(ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name, shareable=True
        ), "Succeeded to update disk that is depend on snapshot to be "
           "shareable ")
