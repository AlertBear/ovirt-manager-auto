"""
3.3 Feature: Storage Virtual disk resize - 9949
https://tcms.engineering.redhat.com/plan/9949
"""

import logging
from utilities.machine import Machine
from art.unittest_lib import attr
from utilities.utils import getIpAddressByHostName
from art.rhevm_api.tests_lib.high_level.disks import \
    create_all_legal_disk_permutations
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.rhevm_api.tests_lib.low_level.disks import waitForDisksState,\
    getStorageDomainDisks, addDisk, attachDisk
from art.rhevm_api.tests_lib.low_level.hosts import waitForHostsStates
from art.rhevm_api.tests_lib.low_level.storagedomains import \
    findMasterStorageDomain, cleanDataCenter, getDomainAddress,\
    get_master_storage_domain_name
from art.rhevm_api.tests_lib.low_level.vms import stop_vms_safely,\
    waitForVMState, deactivateVmDisk, removeDisk, createVm, addSnapshot,\
    removeSnapshot, getVmDisks, preview_snapshot, \
    commit_snapshot, start_vms, undo_snapshot_preview, extend_vm_disk_size,\
    removeVm, waitForVmsStates, wait_for_vm_snapshots
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.storage_api import flushIptables

from art.unittest_lib.common import BaseTestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.test_handler import exceptions
from threading import Thread
import time

from art.test_handler.tools import tcms, bz

import helpers
import config


logger = logging.getLogger(__name__)

TASK_TIMEOUT = 1200
WATCH_TIMOUT = 480
ENUMS = config.ENUMS
FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"
REGEX = "lvextend"

TEST_PLAN_ID = '9949'

disk_args = {
    # Fixed arguments
    'provisioned_size': config.DISK_SIZE,
    'wipe_after_delete': config.BLOCK_FS,
    'storagedomain': config.SD_NAME,
    'bootable': False,
    'shareable': False,
    'active': True,
    'size': config.DISK_SIZE,
    'interface': config.VIRTIO,
    # Custom arguments - change for each disk
    'format': config.FORMAT_COW,
    'sparse': True,
    'alias': "%s_disk"}


vmArgs = {'positive': True,
          'vmName': config.VM_NAME,
          'vmDescription': config.VM_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.FORMAT_COW,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.DISK_SIZE,
          'nic': 'nic1',
          'cobblerAddress': config.COBBLER_ADDRESS,
          'cobblerUser': config.COBBLER_USER,
          'cobblerPasswd': config.COBBLER_PASSWORD,
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.ENUMS['rhel6'],
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }


def setup_module():
    """
    Prepares environment
    """
    logger.info("Preparing datacenter %s with hosts %s",
                config.DC_NAME, config.VDC)
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TESTNAME)

    rc, masterSD = findMasterStorageDomain(True, config.DC_NAME)
    if not rc:
        raise exceptions.StorageDomainException("Could not find master "
                                                "storage domain for dc %s" %
                                                config.DC_NAME)
    vmArgs['storageDomainName'] = masterSD['masterDomain']

    logger.info('Creating vm and installing OS on it')

    if not createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    stop_vms_safely([config.VM_NAME])


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DC_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class DisksPermutationEnvironment(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    __test__ = False
    vm = config.VM_NAME
    shared = False
    new_size = (config.DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        helpers.DISKS_NAMES = create_all_legal_disk_permutations(
            config.SD_NAME, shared=self.shared, block=config.BLOCK_FS,
            size=config.DISK_SIZE)
        assert waitForDisksState(helpers.DISKS_NAMES, timeout=TASK_TIMEOUT)
        stop_vms_safely([self.vm])
        waitForVMState(vm=self.vm, state=ENUMS['vm_state_down'])
        helpers.prepare_disks_for_vm(self.vm, helpers.DISKS_NAMES)

    def tearDown(self):
        """
        Clean environment
        """
        stop_vms_safely([self.vm])
        logger.info("Removing all disks")
        for disk in helpers.DISKS_NAMES:
            deactivateVmDisk(True, self.vm, disk)
            if not removeDisk(True, self.vm, disk):
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk)
            logger.info("Disk %s removed successfully", disk)
        sd_disks = getStorageDomainDisks(config.SD_NAME, get_href=False)
        disks_to_remove = [d.get_alias for d in sd_disks if
                           (not d.get_bootable)]
        for disk in disks_to_remove:
            deactivateVmDisk(True, self.vm, disk)
            status = removeDisk(True, self.vm, disk)
            if not status:
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk)
            logger.info("Disk %s removed successfully", disk)
        logger.info("Finished testCase")


class BasicResize(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    __test__ = False
    vm = config.VM_NAME
    new_size = (config.DISK_SIZE + config.GB)
    host_ip = None
    disk_name = ''
    block_cmd = "iptables -I OUTPUT -d %s -p tcp -j DROP"
    stop_libvirt = "service libvirtd stop"
    disk_args = {}

    def setUp(self):
        """
        Prepare environment
        """
        args = disk_args.copy()
        args.update(self.disk_args)

        self.assertTrue(addDisk(True, **args), "Failed to add disk %s"
                                               % self.disk_args['alias'])
        assert waitForDisksState(self.disk_name)
        stop_vms_safely([self.vm])
        waitForVMState(vm=self.vm, state=ENUMS['vm_state_down'])
        attachDisk(True, self.disk_args['alias'], self.vm)
        assert waitForDisksState(self.disk_name)
        start_vms([self.vm], 1, wait_for_ip=False)
        waitForVMState(vm=self.vm)

    def perform_basic_action(self):
        logger.info("Resizing disk %s", self.disk_name)
        status = extend_vm_disk_size(True, self.vm,
                                     disk=self.disk_name,
                                     provisioned_size=self.new_size)
        self.assertTrue(status, "Failed to resize disk %s to size %s"
                                % (self.disk_name, self.new_size))
        assert waitForDisksState(self.disk_name, timeout=TASK_TIMEOUT)

        logger.info("dd to disk %s", self.disk_name)
        helpers.verify_write_operation_to_disk(self.vm)

        disks_objs = getVmDisks(config.VM_NAME)
        disk_obj = [disk_obj for disk_obj in disks_objs if
                    (not disk_obj.get_bootable())][0]
        datacenter_obj = get_data_center(config.DC_NAME)

        logger.info("Getting volume size")
        lv_size = helpers.get_volume_size(config.HOSTS[0],
                                          config.VDS_USER[0],
                                          config.VDS_PASSWORD[0],
                                          disk_obj,
                                          datacenter_obj)
        self.assertEqual(lv_size, self.new_size / config.GB)

        devices, boot_device = helpers.get_vm_storage_devices(config.VM_NAME)

        start_vms([self.vm], max_workers=1, wait_for_ip=False)
        waitForVMState(self.vm)
        for device in devices:
            size = helpers.get_vm_device_size(config.VM_NAME, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def block_connection_case(self):
        found, master_domain = findMasterStorageDomain(
            True, config.DC_NAME)
        assert found
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, master_domain_ip = getDomainAddress(
            True, master_domain)
        assert found
        master_domain_ip = master_domain_ip['address']
        self.host_ip = getIpAddressByHostName(config.HOSTS[0])
        self.block_cmd = self.block_cmd % master_domain_ip

        t = Thread(target=watch_logs, args=(
            FILE_TO_WATCH, REGEX, self.block_cmd, None,
            self.host_ip, 'root', config.VDC_PASSWORD))
        t.start()

        time.sleep(5)

        logger.info("Resizing disk %s", self.disk_name)
        status = extend_vm_disk_size(True, self.vm,
                                     disk=self.disk_name,
                                     provisioned_size=self.new_size)

        t.join()
        time.sleep(5)
        self.assertTrue(status, "Failed to resize disk %s to size %s"
                                % (self.disk_name, self.new_size))

        logger.info("Unblocking the connection")
        flushIptables(self.host_ip, 'root', config.VDS_PASSWORD[0])
        assert waitForDisksState(self.disk_name, timeout=TASK_TIMEOUT)
        waitForHostsStates(True, config.HOSTS[0])

        disks_objs = getVmDisks(config.VM_NAME)
        disk_obj = [disk_obj for disk_obj in disks_objs if
                    (not disk_obj.get_bootable())][0]
        datacenter_obj = get_data_center(config.DC_NAME)

        logger.info("Getting volume size")
        lv_size = helpers.get_volume_size(config.HOSTS[0],
                                          config.VDS_USER[0],
                                          config.VDS_PASSWORD[0],
                                          disk_obj,
                                          datacenter_obj)
        self.assertEqual(lv_size, self.new_size / config.GB)

        devices, boot_device = helpers.get_vm_storage_devices(config.VM_NAME)

        start_vms([self.vm], max_workers=1, wait_for_ip=False)
        waitForVMState(self.vm)
        for device in devices:
            size = helpers.get_vm_device_size(config.VM_NAME, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def multiple_disks(self, vm_names):
        for vm in vm_names:
            disk_name = getVmDisks(vm)[0].get_alias()
            status = extend_vm_disk_size(True, vm, disk_name,
                                         provisioned_size=self.new_size)
            assert status
        for vm in vm_names:
            disk_name = getVmDisks(vm)[0].get_alias()
            assert waitForDisksState(disk_name)

    def tearDown(self):
        """
        Clean environment
        """
        flushIptables(self.host_ip, 'root', config.VDS_PASSWORD[0])
        self.assertTrue(deactivateVmDisk(True, self.vm, self.disk_name),
                        "Failed to deactivate disks %s" % self.disk_name)
        self.assertTrue(removeDisk(True, self.vm, self.disk_name),
                        "Failed to remove disks %s" % self.disk_name)


@attr(tier=0)
class TestCase336099(DisksPermutationEnvironment):
    """
    Resize virtual disk after snapshot creation
    https://tcms.engineering.redhat.com/case/336099/?from_plan=9949
    """
    __test__ = True
    tcms_test_case = '336099'
    snap_description = 'snap_%s' % tcms_test_case

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_virtual_disk_resize_after_snapshot_creation(self):
        """
        - VM with 6G disk and OS
        - Create a snapshot to the VM
        - Resize the VM disk, add 1G to it
        """
        logger.info("Creating Snapshot")
        self.assertTrue(addSnapshot(True, self.vm, self.snap_description),
                        "Failed to add snapshot %s" % self.snap_description)

        wait_for_vm_snapshots(self.vm, ENUMS['snapshot_state_ok'])

        for disk in helpers.DISKS_NAMES:
            logger.info("Resizing disk %s", disk)

            status = extend_vm_disk_size(True, self.vm,
                                         disk=disk,
                                         provisioned_size=self.new_size)

            self.assertTrue(status, "Failed to resize disk %s to size %s"
                                    % (disk, self.new_size))
        assert waitForDisksState(helpers.DISKS_NAMES, timeout=TASK_TIMEOUT)

        devices, boot_device = helpers.get_vm_storage_devices(config.VM_NAME)

        start_vms([self.vm], max_workers=1, wait_for_ip=False)
        waitForVMState(self.vm)
        for device in devices:
            size = helpers.get_vm_device_size(config.VM_NAME, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def tearDown(self):
        super(TestCase336099, self).tearDown()

        if not removeSnapshot(True, config.VM_NAME, self.snap_description):
            raise exceptions.SnapshotException("Failed to remove snapshot %s"
                                               % self.snap_description)


@attr(tier=0)
class TestCase336100(DisksPermutationEnvironment):
    """
    Commit snapshot after resizing the disk
    https://tcms.engineering.redhat.com/case/336100/?from_plan=9949
    """
    __test__ = True
    tcms_test_case = '336100'
    snap_description = 'snap_%s' % tcms_test_case
    is_preview = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    @bz('1101405')
    def test_Commit_snapshot_after_disk_resize(self):
        """
        - VM with 6G disk and OS
        - Create a snapshot to the VM
        - Resize the VM disk, add 1G to it
        - Shutdown the VM and preview the snapshot
        - Commit the snapshot
        - The disk should have the size it was by the time we
          created the snapshot (6G)
        """
        logger.info("Creating Snapshot")
        self.assertTrue(addSnapshot(True, self.vm, self.snap_description),
                        "Failed to add snapshot %s" % self.snap_description)
        wait_for_vm_snapshots(self.vm, ENUMS['snapshot_state_ok'])

        for disk in helpers.DISKS_NAMES:
            status = extend_vm_disk_size(True, self.vm,
                                         disk=disk,
                                         provisioned_size=self.new_size)
            self.assertTrue(status, "Failed to resize disk %s to size %s"
                                    % (disk, self.new_size))
        assert waitForDisksState(helpers.DISKS_NAMES, timeout=TASK_TIMEOUT)

        status = preview_snapshot(True, self.vm, self.snap_description)
        self.is_preview = status
        assert status

        status = commit_snapshot(True, self.vm)
        start_vms([self.vm], 1, wait_for_ip=False)
        waitForVMState(self.vm)
        assert status
        self.is_preview = not status
        vm_disks = getVmDisks(self.vm)
        disks_sizes = [disk.get_size() for disk in vm_disks if
                       (not disk.get_bootable())]
        for size in disks_sizes:
            assert size == (self.new_size - config.GB)

    def tearDown(self):
        if self.is_preview:
            undo_snapshot_preview(True, self.vm)
            wait_for_vm_snapshots(self.vm, ENUMS['snapshot_state_ok'])

        super(TestCase336100, self).tearDown()

        if not removeSnapshot(True, config.VM_NAME, self.snap_description):
            raise exceptions.SnapshotException("Failed to remove snapshot %s"
                                               % self.snap_description)


@attr(tier=0)
class TestCase287466(BasicResize):
    """
    Virtual disk resize - preallocated  block disk
    https://tcms.engineering.redhat.com/case/287466/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '287466'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        super(TestCase287466, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preallocated_block_resize(self):
        """
        - VM with 6G preallocated disk and OS
        - Resize the VM disk to 7G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=0)
class TestCase297017(BasicResize):
    """
    Virtual disk resize - Thin block disk
    https://tcms.engineering.redhat.com/case/297017/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '297017'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = True
        self.disk_args['format'] = config.FORMAT_COW
        super(TestCase297017, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_thin_block_resize(self):
        """
        - VM with 6G thin disk and OS
        - Resize the VM disk to 7G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=0)
class TestCase287467(BasicResize):
    """
    Virtual disk resize - preallocated file disk
    https://tcms.engineering.redhat.com/case/287467/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE not in config.BLOCK_TYPES
    tcms_test_case = '287467'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        super(TestCase287467, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preallocated_file_resize(self):
        """
        - VM with 6G preallocated disk and OS
        - Resize the VM disk to 7G total
        - Send IOs to disk
        - Check size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=0)
class TestCase297018(BasicResize):
    """
    Virtual disk resize - Thin file disk
    https://tcms.engineering.redhat.com/case/297018/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE not in config.BLOCK_TYPES
    tcms_test_case = '297018'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = True
        self.disk_args['format'] = config.FORMAT_COW
        super(TestCase297018, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_thin_file_resize(self):
        """
        - VM with 6G preallocated disk and OS
        - Resize the VM disk to 7G total
        - Send IOs to disk
        - Check size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=1)
class TestCase297090(BasicResize):
    """
    block connectivity from host to storage domain - preallocated disk
    https://tcms.engineering.redhat.com/case/297090/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '297090'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        super(TestCase297090, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_block_connection_preallocated_resize(self):
        """
        - VM with 6G preallocated disk and OS
        - Resize the VM disk to 7G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@attr(tier=1)
class TestCase297089(BasicResize):
    """
    block connectivity from host to storage domain - sparse disk
    https://tcms.engineering.redhat.com/case/297089/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '297089'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        super(TestCase297089, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_block_connection_sparse_resize(self):
        """
        - VM with 6G thin disk and OS
        - Resize the VM disk to 7G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@attr(tier=1)
class TestCase287468(BasicResize):
    """
    Resize shared disk
    https://tcms.engineering.redhat.com/case/287468/?from_plan=9949
    """
    __test__ = True
    tcms_test_case = '287468'
    test_vm_name = "vm_%s" % tcms_test_case

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        self.disk_args['shareable'] = True
        super(TestCase287468, self).setUp()
        self.test_vm_name = 'test_%s' % self.tcms_test_case
        vmArgs['vmName'] = self.test_vm_name
        vmArgs['storageDomainName'] = \
            get_master_storage_domain_name(config.DC_NAME)

        logger.info('Creating vm and installing OS on it')
        if not createVm(**vmArgs):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)
        assert waitForVMState(self.test_vm_name)
        assert attachDisk(True, self.disk_args['alias'], self.test_vm_name)
        start_vms([self.test_vm_name], max_workers=1, wait_for_ip=False)
        assert waitForVMState(self.test_vm_name)
        assert waitForDisksState(self.disk_name)
        stop_vms_safely([self.vm, self.test_vm_name])

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_shared_block_disk_resize(self):
        """
        - 2 VM with 6G RAW disk and OS
        - 1 shared disk
        - Resize the shared disk to 7G total
        - Check LV size on VDSM and disk size on guest of both vms
        """
        start_vms([self.vm, self.test_vm_name], max_workers=2,
                  wait_for_ip=False)
        names = "%s, %s" % (self.vm, self.test_vm_name)
        assert waitForVmsStates(True, names)
        self.perform_basic_action()

        devices, boot_device = \
            helpers.get_vm_storage_devices(self.test_vm_name)

        for device in devices:
            size = helpers.get_vm_device_size(self.test_vm_name, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def tearDown(self):
        stop_vms_safely([self.test_vm_name, self.vm])
        super(TestCase287468, self).tearDown()
        self.disk_args['shareable'] = False

        assert removeVm(True, self.test_vm_name, stopVM='true', wait=True)


@attr(tier=1)
class TestCase287469(BasicResize):
    """
    Extend disk to more than available capacity
    https://tcms.engineering.redhat.com/case/287469/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '287469'
    new_size = (config.DISK_SIZE + config.GB * config.STORAGE_SIZE)

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = False
        self.disk_args['format'] = config.FORMAT_RAW
        super(TestCase287469, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_thin_block_resize(self):
        """
        - VM with 6G thin disk and OS
        - Resize the VM disk to 56G total
        """
        logger.info("Resizing disk %s", self.disk_name)
        status = extend_vm_disk_size(False, self.vm,
                                     disk=self.disk_name,
                                     provisioned_size=self.new_size)
        self.assertTrue(status, "Succeeded to resize disk %s to new size %s"
                                % (self.disk_name, self.new_size))

    def tearDown(self):
        assert waitForDisksState(self.disk_name)
        super(TestCase287469, self).tearDown()


@attr(tier=1)
class TestCase297085(BasicResize):
    """
    Stop libvirt service during disk extension
    https://tcms.engineering.redhat.com/case/297085/?from_plan=9949
    """
    __test__ = True
    tcms_test_case = '297085'
    service_to_start = 'libvirtd'
    look_for_regex = 'Run and protect: extendVolumeSize'

    def setUp(self):
        """
        Creating disk
        """
        self.disk_args['alias'] = 'disk_%s' % self.tcms_test_case
        self.disk_name = self.disk_args['alias']
        self.disk_args['sparse'] = True
        self.disk_args['format'] = config.FORMAT_COW
        super(TestCase297085, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_stop_libvirt_during_resize(self):
        """
        - VM with 6G thin disk and OS
        - Resize the VM disk to 7G total
        - When SPM get The task, stop libvirt service
        """
        host_ip = getIpAddressByHostName(config.HOSTS[0])
        t = Thread(target=watch_logs, args=(
            FILE_TO_WATCH, self.look_for_regex, self.stop_libvirt, None,
            host_ip, 'root', config.VDC_PASSWORD))
        t.start()

        time.sleep(5)

        logger.info("Resizing disk %s", self.disk_name)
        status = extend_vm_disk_size(True, self.vm,
                                     disk=self.disk_name,
                                     provisioned_size=self.new_size)
        t.join()
        self.assertTrue(status, "Failed to resize disk %s to size %s"
                                % (self.disk_name, self.new_size))
        host_machine = Machine(host=host_ip, user=config.VDS_USER[0],
                               password=config.VDS_PASSWORD[0]).util('linux')
        host_machine.startService(self.service_to_start)
        assert waitForDisksState(self.disk_name, timeout=TASK_TIMEOUT)
        logger.info("dd to disk %s", self.disk_name)
        helpers.verify_write_operation_to_disk(self.vm)
        logger.info("Getting volume size")

        disks_objs = getVmDisks(config.VM_NAME)
        disk_obj = [disk_obj for disk_obj in disks_objs if
                    (not disk_obj.get_bootable())][0]
        datacenter_obj = get_data_center(config.DC_NAME)

        lv_size = helpers.get_volume_size(config.HOSTS[0],
                                          config.VDS_USER[0],
                                          config.VDS_PASSWORD[0],
                                          disk_obj,
                                          datacenter_obj)
        self.assertEqual(lv_size, self.new_size / config.GB)


@attr(tier=2)
class TestCase287477(BasicResize):
    """
    Increase and decrease multiple disks
    https://tcms.engineering.redhat.com/case/287477/?from_plan=9949
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '287477'
    vm_name = "vm_%s_%s"
    vm_count = 3

    new_size = (config.DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating disk
        """
        self.vm_names = list()
        rc, masterSD = findMasterStorageDomain(True, config.DC_NAME)
        if not rc:
            raise exceptions.StorageDomainException("Could not find master "
                                                    "storage domain "
                                                    "for dc %s" %
                                                    config.DC_NAME)
        vmArgs['storageDomainName'] = masterSD['masterDomain']
        vmArgs['installation'] = False

        logger.info('Creating vm and installing OS on it')

        for i in range(self.vm_count):
            self.vm_name = "vm_%s_%s"
            self.vm_name = self.vm_name % (self.tcms_test_case, i)
            vmArgs['vmName'] = self.vm_name
            if not createVm(**vmArgs):
                raise exceptions.VMException('Unable to create vm %s for test'
                                             % self.vm_name)
            self.vm_names.append(self.vm_name)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_resize_same_SD(self):
        """
        - 5 vms with OS, disks on same SD
        - resize the first 3 virtual disks to 20G (increase size)
        - resize the 2 left disks to 10G (decrease size) (NOT supported)
        - all resizing tasks should run together (as possible) without waiting
          for tasks to complete.
        """
        self.multiple_disks(self.vm_names)

    def tearDown(self):
        for vm in self.vm_names:
            assert removeVm(True, vm)


@attr(tier=2)
class TestCase287478(BasicResize):
    """
    Increase and decrease multiple disks
    https://tcms.engineering.redhat.com/case/287478/?from_plan=9949
    Currently __test__ = False - disk shrink doesn't support
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '287478'
    vm_name = "vm_%s_%s"
    vm_count = 2
    new_size = (config.DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating disk
        """
        self.vm_names = list()
        vmArgs['installation'] = False

        logger.info('Creating vm and installing OS on it')
        sd_list = [config.SD_NAME, config.SD_NAME_1]

        for i, sd in zip(range(self.vm_count), sd_list):
            self.vm_name = "vm_%s_%s"
            vmArgs['storageDomainName'] = sd
            self.vm_name = self.vm_name % (self.tcms_test_case, i)
            vmArgs['vmName'] = self.vm_name
            if not createVm(**vmArgs):
                raise exceptions.VMException('Unable to create vm %s for test'
                                             % self.vm_name)
            self.vm_names.append(self.vm_name)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_resize_different_SD(self):
        """
        - 5 vms with OS, disks on different SD
        - resize the first 3 virtual disks to 20G (increase size)
        - resize the 2 left disks to 10G (decrease size) (NOT supported)
        - all resizing tasks should run together (as possible) without waiting
          for tasks to complete.
        """
        self.multiple_disks(self.vm_names)

    def tearDown(self):
        vmArgs['installation'] = True
        for vm in self.vm_names:
            assert removeVm(True, vm)
