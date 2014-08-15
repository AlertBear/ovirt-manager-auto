"""
Storage VM Floating Disk
"""
import logging
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level import disks, vms, storagedomains

import config
VM_1, VM_2 = config.VM1_NAME, config.VM2_NAME
ENUMS = config.ENUMS

logger = logging.getLogger(__name__)


@attr(tier=0)
class TestCase174614(TestCase):
    """
    Test Floating disk is functional
    Spected system: 2 vms with state down
    """
    __test__ = True

    disk_name = "floating"
    tcms_plan_id = '6458'
    tcms_test_case = '174614'

    def setUp(self):
        """Get the sd and make sure the VM's are down"""
        self.storage_domain = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].get_name()
        assert vms.checkVmState(True, VM_1, ENUMS["vm_state_down"])
        assert vms.checkVmState(True, VM_2, ENUMS["vm_state_down"])

    @tcms(tcms_plan_id, tcms_test_case)
    def test_floating_disk(self):
        """Creates a floating disk and assign it to different vms"""
        logger.info("Creating Floating Disk")
        self.assertTrue(
            disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                size=config.GB, interface=config.VIRTIO_SCSI,
                format=ENUMS['format_cow'], storagedomain=self.storage_domain))

        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        logger.info("Attaching disk to vm %s" % VM_1)
        self.assertTrue(disks.attachDisk(True, self.disk_name, VM_1))
        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        self.assertTrue(vms.startVm(True, VM_1))
        # TBD Extra validation How tests disk is working
        self.assertTrue(vms.stopVm(True, VM_1))

        logger.info("Dettaching disk from vm %s" % VM_1)
        self.assertTrue(disks.detachDisk(True, self.disk_name, VM_1))

        logger.info("Attaching disk to vm %s" % VM_2)
        self.assertTrue(disks.attachDisk(True, self.disk_name, VM_2))
        self.assertTrue(disks.waitForDisksState(disksNames=[self.disk_name]))
        self.assertTrue(vms.startVm(True, VM_2))
        # TBD Extra validation How tests disk is working

    def tearDown(self):
        """Make sure vms are down and the disk is removed"""
        logger.info("Tearing down floating disk")
        if not vms.checkVmState(True, VM_1, ENUMS["vm_state_down"]):
            assert vms.stopVm(True, VM_1)
        assert vms.stopVm(True, VM_2)
        assert disks.deleteDisk(True, self.disk_name)
