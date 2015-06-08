"""
Storage VM Floating Disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Hosted_Engine_Sanity
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level import disks, storagedomains, vms
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr
from art.test_handler.settings import opts

ENUMS = config.ENUMS

logger = logging.getLogger(__name__)


@attr(tier=0)
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
        self.vm_1 = config.VM1_NAME % self.storage
        self.vm_2 = config.VM2_NAME % self.storage
        """Start the two vms and get the storage_domain name"""
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        for vm in [self.vm_1, self.vm_2]:
            assert vms.startVm(True, vm, wait_for_status=ENUMS['vm_state_up'])

    @polarion("RHEVM3-11513")
    def test_shared(self):
        """Creates a shared disk and assign it to different vms
        """
        logger.info("Creating sharable raw disk")
        self.assertTrue(
            disks.addDisk(
                True, alias=self.disk_name, provisioned_size=config.GB,
                size=config.GB, interface=config.VIRTIO_SCSI,
                format=ENUMS['format_raw'], storagedomain=self.storage_domain,
                shareable=True, sparse=False)
        )

        self.assertTrue(disks.wait_for_disks_status(disks=[self.disk_name]))
        logger.info("Attaching disk to vm %s" % self.vm_1)
        self.assertTrue(disks.attachDisk(True, self.disk_name, self.vm_1))
        self.assertTrue(disks.wait_for_disks_status(disks=[self.disk_name]))
        self.assertTrue(
            vms.waitForVmDiskStatus(self.vm_1, True, diskAlias=self.disk_name,
                                    sleep=1)
        )
        # TODO: TBD Extra validation ?

        logger.info("Attaching disk to vm %s" % self.vm_2)
        self.assertTrue(disks.attachDisk(True, self.disk_name, self.vm_2))
        self.assertTrue(disks.wait_for_disks_status(disks=[self.disk_name]))
        self.assertTrue(
            vms.waitForVmDiskStatus(self.vm_1, True, diskAlias=self.disk_name,
                                    sleep=1)
        )
        self.assertTrue(
            vms.waitForVmDiskStatus(self.vm_2, True, diskAlias=self.disk_name,
                                    sleep=1)
        )
        # TODO: TBD Extra validation ?

    def tearDown(self):
        """
        Make sure vms are down and the disk is removed
        """
        assert vms.stopVms(",".join([self.vm_1, self.vm_2]), wait='true')
        assert disks.deleteDisk(True, self.disk_name)


@attr(tier=1)
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
            vms.createVm(
                True, vm_name, vm_name, config.CLUSTER_NAME, nic=nic,
                placement_host=config.HOSTS[0], network=config.MGMT_BRIDGE)
            self.vm_names.append(vm_name)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.disk_name = 'disk_%s' % self.polarion_test_case
        logger.info("Creating disk")
        assert disks.addDisk(
            True, alias=self.disk_name, shareable=True, bootable=False,
            size=self.disk_size, storagedomain=storage_domain,
            format=ENUMS['format_raw'], interface=config.VIRTIO_SCSI,
            sparse=False)
        assert disks.wait_for_disks_status(self.disk_name)
        logger.info("Disk created")

        for vm in self.vm_names:
            assert disks.attachDisk(True, self.disk_name, vm, True)

        vms.start_vms(self.vm_names, max_workers=config.MAX_WORKERS,
                      wait_for_ip=False)

    def tearDown(self):
        assert vms.removeVms(True, self.vm_names, stop='true')
        if self.disk_name is not None:
            assert disks.deleteDisk(True, self.disk_name)
