"""
Storage VM Floating Disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Hosted_Engine_Sanity
"""
import config
import logging
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level import disks, vms, storagedomains

ENUMS = config.ENUMS

logger = logging.getLogger(__name__)


@attr(tier=0)
class TestCase11518(TestCase):
    """
    Test Floating disk is functional
    Spected system: 2 vms with state down
    """
    __test__ = True
    disk_name = "floating"
    polarion_test_case = '11518'

    def setUp(self):
        self.vm_1 = config.VM1_NAME % self.storage
        self.vm_2 = config.VM2_NAME % self.storage
        """Get the sd and make sure the VM's are down"""
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        assert vms.checkVmState(True, self.vm_1, ENUMS["vm_state_down"])
        assert vms.checkVmState(True, self.vm_2, ENUMS["vm_state_down"])

    @polarion("RHEVM3-11518")
    def test_floating_disk(self):
        """Creates a floating disk and assign it to different vms"""
        logger.info("Creating Floating Disk")
        self.assertTrue(
            disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                size=config.GB, interface=config.VIRTIO_SCSI,
                format=ENUMS['format_cow'], storagedomain=self.storage_domain))

        self.assertTrue(
            disks.wait_for_disks_status(
                disks=[self.disk_name]
            )
        )
        logger.info("Attaching disk to vm %s" % self.vm_1)
        self.assertTrue(disks.attachDisk(True, self.disk_name, self.vm_1))
        self.assertTrue(
            disks.wait_for_disks_status(
                disks=[self.disk_name]
            )
        )
        self.assertTrue(vms.startVm(True, self.vm_1))
        # TODO Extra validation How tests disk is working
        self.assertTrue(vms.stopVm(True, self.vm_1))

        logger.info("Dettaching disk from vm %s" % self.vm_1)
        self.assertTrue(disks.detachDisk(True, self.disk_name, self.vm_1))

        logger.info("Attaching disk to vm %s" % self.vm_2)
        self.assertTrue(disks.attachDisk(True, self.disk_name, self.vm_2))
        self.assertTrue(
            disks.wait_for_disks_status(
                disks=[self.disk_name]
            )
        )
        self.assertTrue(vms.startVm(True, self.vm_2))
        # TODO Extra validation How tests disk is working

    def tearDown(self):
        """Make sure vms are down and the disk is removed"""
        logger.info("Tearing down floating disk")
        if not vms.checkVmState(True, self.vm_1, ENUMS["vm_state_down"]):
            assert vms.stopVm(True, self.vm_1)
        assert vms.stopVm(True, self.vm_2)
        assert disks.deleteDisk(True, self.disk_name)
