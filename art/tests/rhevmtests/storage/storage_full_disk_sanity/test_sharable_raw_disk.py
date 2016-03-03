"""
Storage VM Floating Disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Hosted_Engine_Sanity
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sds,
    vms as ll_vms,
)
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr
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
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])

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
        logger.info("Creating sharable raw disk")
        self.assertTrue(
            ll_disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                size=config.GB, interface=config.VIRTIO_SCSI,
                format=config.RAW_DISK, storagedomain=self.storage_domain,
                shareable=True, sparse=False
            )
        )

        self.assertTrue(ll_disks.wait_for_disks_status(disks=[self.disk_name]))
        logger.info("Attaching disk to vm %s" % self.vm_1)
        self.assertTrue(ll_disks.attachDisk(True, self.disk_name, self.vm_1))
        self.assertTrue(ll_disks.wait_for_disks_status(disks=[self.disk_name]))
        self.assertTrue(
            ll_vms.waitForVmDiskStatus(
                self.vm_1, True, self.disk_name, sleep=1
            )
        )
        # TODO: Extra validation ?

        logger.info("Attaching disk to vm %s", self.vm_2)
        self.assertTrue(ll_disks.attachDisk(True, self.disk_name, self.vm_2))
        self.assertTrue(ll_disks.wait_for_disks_status([self.disk_name]))
        self.assertTrue(
            ll_vms.waitForVmDiskStatus(
                self.vm_1, True, self.disk_name, sleep=1
            )
        )
        self.assertTrue(
            ll_vms.waitForVmDiskStatus(
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
            size=self.disk_size, storagedomain=storage_domain,
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
