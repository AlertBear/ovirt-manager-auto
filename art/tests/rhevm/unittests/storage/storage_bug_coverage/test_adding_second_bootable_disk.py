"""
TCMS Test Case 355191 355191, exposing BZ 1066834
Add a second bootable disks to a vm should fail
"""
import logging
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms, storagedomains, disks
from art.test_handler.tools import bz, tcms

import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
BZID = "1066834"
GB = 1024**3
VM_NAME = "vm_%s" % BZID


def _create_vm(vm_name, disk_interface,
               sparse=True, volume_format=ENUMS['format_cow'],
               vm_type=config.VM_TYPE_DESKTOP):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    storage_domain = storagedomains.getDCStorages(
        config.DATA_CENTER_NAME, False)[0].get_name()
    logger.info("Creating VM %s at SD %s", vm_name, storage_domain)
    return vms.createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
        password=config.VM_LINUX_PASSWORD, type=vm_type, installation=False,
        slim=True, network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
        bootable=True)


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


class TestCase355191(TestCase):
    """
    Test case 355191 - Test that exposes BZ1066834

    https://tcms.engineering.redhat.com/case/355191/edit/?from_plan=2515
    """
    tcms_plan_id = '2515'
    tcms_test_case = '280628'
    expected_disk_number = 2
    __test__ = True

    def setUp(self):
        """
        Create a vm with a bootable disk
        """
        assert _create_vm(VM_NAME, ENUMS['interface_virtio_scsi'])
        self.storage_domain = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].get_name()

    @bz(BZID)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_add_multiple_bootable_disks(self):
        """
        Verify adding a second bootable disk should fail
        """
        disks = vms.getVmDisks(VM_NAME)
        assert len(disks) == 1
        assert disks[0].get_bootable()

        # Could add a non bootable disk
        logger.info("Adding a new non bootable disk works")
        self.second_disk = "second_disk_%s" % BZID
        assert vms.addDisk(
            True, VM_NAME, GB, wait=True,
            storagedomain=self.storage_domain, bootable=False,
            alias=self.second_disk)

        disks = vms.getVmDisks(VM_NAME)
        assert len(disks) == self.expected_disk_number
        assert False in [disk.get_bootable() for disk in disks]

        logger.info("Adding a second bootable disk to vm %s should fail",
                    VM_NAME)
        self.bootable_disk = "bootable_disk_%s" % BZID
        self.assertTrue(vms.addDisk(
            False, VM_NAME, GB, wait=True, alias=self.bootable_disk,
            storagedomain=self.storage_domain, bootable=True),
            "Shouldn't be possible to add a second bootable disk")

    def tearDown(self):
        """
        Remove created vm
        """
        # If it fails, the disk are still being added, wait for them
        disks_aliases = [disk.get_alias() for disk in vms.getVmDisks(VM_NAME)]
        disks.waitForDisksState(disksNames=disks_aliases)
        assert vms.removeVm(True, VM_NAME)
