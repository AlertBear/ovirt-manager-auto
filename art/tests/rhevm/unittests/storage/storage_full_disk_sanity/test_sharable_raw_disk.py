"""
Storage VM Floating Disk
"""
import logging
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr

from art.rhevm_api.tests_lib.low_level import disks, storagedomains
from art.test_handler.tools import tcms
import config

VM_1, VM_2 = config.VM1_NAME, config.VM2_NAME
ENUMS = config.ENUMS

logger = logging.getLogger(__name__)

from art.rhevm_api.tests_lib.low_level import vms


@attr(tier=0)
class TestCase174621(TestCase):
    """
    Test sharing disk
    Expected system: 2 vms with state down
    """
    __test__ = True

    tcms_plan_id = '6458'
    tcms_test_case = '174621'
    disk_name = "shareableDisk"

    def setUp(self):
        """Start the two vms and get the storage_domain name"""
        self.storage_domain = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].get_name()
        for vm in [VM_1, VM_2]:
            assert vms.startVm(True, vm, wait_for_status=ENUMS['vm_state_up'])

    @tcms(tcms_plan_id, tcms_test_case)
    def test_shared(self):
        """Creates a shared disk and assign it to different vms
        """
        logger.info("Creating sharable raw disk")
        self.assertTrue(
            disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                size=config.GB, interface=config.VIRTIO_SCSI,
                format=ENUMS['format_raw'], storagedomain=self.storage_domain,
                shareable=True, sparse=False))

        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        logger.info("Attaching disk to vm %s" % VM_1)
        self.assertTrue(disks.attachDisk(True, self.disk_name, VM_1))
        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        self.assertTrue(vms.waitForVmDiskStatus(VM_1, True,
                        diskAlias=self.disk_name, timeout=2, sleep=1))
        # TBD Extra validation ?

        logger.info("Attaching disk to vm %s" % VM_2)
        self.assertTrue(disks.attachDisk(True, self.disk_name, VM_2))
        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        self.assertTrue(vms.waitForVmDiskStatus(VM_1, True,
                        diskAlias=self.disk_name, timeout=2, sleep=1))
        self.assertTrue(vms.waitForVmDiskStatus(VM_2, True,
                        diskAlias=self.disk_name, timeout=2, sleep=1))
        # TBD Extra validation ?

    def tearDown(self):
        """
        Make sure vms are down and the disk is removed
        """
        assert vms.stopVms(",".join([VM_1, VM_2]), wait='true')
        assert disks.deleteDisk(True, self.disk_name)


@attr(tier=1)
class TestCase275816(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=834893
    scenario:
    * creates 4 VMs with nics but without disks
    * creates a shared disks
    * attaches the disk to the vms one at a time
    * runs all the vms on one host

    https://tcms.engineering.redhat.com/case/275816/?from_plan=9583
    """
    __test__ = True

    tcms_plan_id = '9583'
    tcms_test_case = '275816'
    vm_names = []
    disk_name = None
    disk_size = 1 * config.GB

    @tcms(tcms_plan_id, tcms_test_case)
    def test_several_vms_with_same_shared_disk_on_one_host_test(self):
        """ tests if running a few VMs with the same shared disk on the same
            host works correctly
        """
        for i in range(4):
            vm_name = "vm_%s_%s" % (self.tcms_test_case, i)
            nic = "nic_%s" % i
            vms.createVm(
                True, vm_name, vm_name, config.CLUSTER_NAME, nic=nic,
                placement_host=config.HOSTS[0])
            self.vm_names.append(vm_name)
        storage_domain_name = storagedomains.getDCStorages(
            config.DEFAULT_DATA_CENTER_NAME, False)[0].name
        self.disk_name = 'disk_%s' % self.tcms_test_case
        logger.info("Creating disk")
        assert disks.addDisk(
            True, alias=self.disk_name, shareable=True, bootable=False,
            size=self.disk_size, storagedomain=storage_domain_name,
            format=ENUMS['format_raw'], interface=config.VIRTIO_SCSI,
            sparse=False)
        assert disks.waitForDisksState(self.disk_name)
        logger.info("Disk created")

        for vm in self.vm_names:
            assert disks.attachDisk(True, self.disk_name, vm, True)

        vms.start_vms(self.vm_names, max_workers=config.MAX_WORKERS,
                      wait_for_ip=False)

    def tearDown(self):
        assert vms.removeVms(True, self.vm_names, stop='true')
        if self.disk_name is not None:
            assert disks.deleteDisk(True, self.disk_name)
