"""
3.3 Feature: Storage Virtual disk resize
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Virtual_Disk_Resize
"""
import config
import helpers
import logging
import time
from threading import Thread
from utilities.machine import Machine
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as BaseTestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dcs,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sds,
    vms as ll_vms
)
from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks,
)
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.storage_api import flushIptables
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

DISK_RESIZE_TIMEOUT = 1200
WATCH_TIMOUT = 480
NFS = config.STORAGE_TYPE_NFS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP


class BaseClass(BaseTestCase):
    """
    Prepares environment
    """
    polarion_test_case = None

    def setUp(self):
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.vm_name = "%s_%s_%s" % (
            config.VM_NAME, self.storage, self.polarion_test_case
        )
        args = config.create_vm_args.copy()
        args['storageDomainName'] = self.storage_domain
        args['vmName'] = self.vm_name

        logger.info('Creating vm %s and installing OS on it', self.vm_name)
        if not storage_helpers.create_vm_or_clone(**args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm_name
            )

    def tearDown(self):
        """
        Remove vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


class DisksPermutationEnvironment(BaseClass):
    """
    A class with common setup and teardown methods
    """
    __test__ = False
    shared = False
    new_size = (config.DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        super(DisksPermutationEnvironment, self).setUp()
        block = self.storage in config.BLOCK_TYPES
        self.disk_names = hl_disks.create_all_legal_disk_permutations(
            self.storage_domain, shared=self.shared,
            block=block, size=config.DISK_SIZE,
            interfaces=storage_helpers.INTERFACES
        )
        if not ll_disks.wait_for_disks_status(self.disk_names):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )
        storage_helpers.prepare_disks_for_vm(self.vm_name, self.disk_names)


class BasicResize(BaseClass):
    """
    A class with common setup and teardown methods
    """
    __test__ = False
    new_size = (config.DISK_SIZE + config.GB)
    host_ip = None
    block_cmd = "iptables -I OUTPUT -d %s -p tcp -j DROP"
    stop_libvirt = "service libvirtd stop"
    start_libvirt = "service libvirtd start"
    test_disk_args = {}

    def setUp(self):
        """
        Prepare environment
        """
        super(BasicResize, self).setUp()
        self.disk_args = config.disk_args.copy()
        self.disk_args.update(self.test_disk_args)
        self.disk_args['storagedomain'] = self.storage_domain
        self.disk_args['alias'] = "disk_%s" % self.polarion_test_case
        self.disk_name = self.disk_args['alias']

        self.assertTrue(
            ll_disks.addDisk(True, **self.disk_args),
            "Failed to add disk %s" % self.disk_name
        )
        if not ll_disks.wait_for_disks_status(self.disk_name):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )
        ll_disks.attachDisk(True, self.disk_name, self.vm_name)
        if not ll_disks.wait_for_disks_status(self.disk_name):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )
        ll_vms.start_vms(
            [self.vm_name], 1, wait_for_status=config.VM_UP, wait_for_ip=False
        )

        self.host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(self.host)

    def perform_basic_action(self):
        """
        1) Resize vm's disk
        2) start to write using 'dd'
        3) Check that disk's size is actually growing
        """
        testflow.step("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            True, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        if not status:
            raise exceptions.DiskException(
                "Failed to resize disk %s to size %s"
                % (self.disk_name, self.new_size)
            )
        if not ll_disks.wait_for_disks_status(
            self.disk_name, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )

        # TODO: Check the capacity value in getVolumeInfo
        logger.info("dd to disk %s", self.disk_name)
        if self.storage in config.BLOCK_TYPES:
            # For block devices, the disk size (lv) will increase by chunks of
            # 1 GB after a certain treshold is surpassed. Copy less than the
            # supposed extended size so the lv will not grow bigger than the
            # extended size.
            dd_size = self.new_size - 600 * config.MB
        else:
            # For file devices the true size will be the same as the dd size.
            dd_size = self.new_size
        ecode, output = storage_helpers.perform_dd_to_disk(
            self.vm_name, self.disk_name, size=dd_size
        )
        testflow.step(
            "Performing 'dd' command to extended disk %s", self.disk_name
        )
        self.assertTrue(ecode, "dd command failed. output: %s" % output)
        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [disk_obj for disk_obj in disks_objs if
                    (self.disk_name == disk_obj.get_alias())][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        testflow.step(
            "Checking volume size for disk %s in host %s ",
            disk_obj.get_alias(), self.host
        )
        lv_size = helpers.get_volume_size(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, disk_obj,
            datacenter_obj
        )
        self.assertEqual(lv_size, self.new_size / config.GB)
        devices, boot_device = helpers.get_vm_storage_devices(self.vm_name)

        for device in devices:
            size = helpers.get_vm_device_size(self.vm_name, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def block_connection_case(self):
        """
        Blocks connection between the host and the storage domain when
        'lvextend' appears in the vdsm.log
        """
        domain_name = ll_vms.get_vms_disks_storage_domain_name(self.vm_name)
        found, storage_domain_ip = ll_sds.getDomainAddress(
            True, domain_name)
        storage_domain_ip = storage_domain_ip['address']
        self.block_cmd = self.block_cmd % storage_domain_ip

        t = Thread(target=watch_logs, args=(
            config.VDSM_LOG, "lvextend", self.block_cmd, None,
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW))
        t.start()
        time.sleep(5)

        logger.info("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            True, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        t.join()
        if not status:
            raise exceptions.DiskException(
                "Failed to resize disk %s to size %s" %
                (self.disk_name, self.new_size)
            )
        logger.info("Unblocking the connection")
        flushIptables(self.host_ip, config.HOSTS_USER, config.HOSTS_PW)
        if not ll_disks.wait_for_disks_status(
            self.disk_name, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )
        ll_hosts.waitForHostsStates(True, self.host)

        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [
            disk_obj for disk_obj in disks_objs if not
            ll_vms.is_bootable_disk(self.vm_name, disk_obj.get_id())
        ][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        logger.info("Getting volume size")
        lv_size = helpers.get_volume_size(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, disk_obj,
            datacenter_obj
        )
        self.assertEqual(lv_size, self.new_size / config.GB)
        devices, boot_device = helpers.get_vm_storage_devices(self.vm_name)
        ll_vms.start_vms([self.vm_name], max_workers=1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)
        for device in devices:
            size = helpers.get_vm_device_size(self.vm_name, device)
            self.assertEqual(int(size), (self.new_size / config.GB))

    def multiple_disks(self, vm_names):
        """
        Extend multiple disks
        """
        for vm in vm_names:
            disk_name = ll_vms.getVmDisks(vm)[0].get_alias()
            status = ll_vms.extend_vm_disk_size(
                True, vm, disk_name, provisioned_size=self.new_size
            )
            if not status:
                raise exceptions.DiskException(
                    "Failed to extend vm's disk %s" % self.disk_name
                )
        for vm in vm_names:
            disk_name = ll_vms.getVmDisks(vm)[0].get_alias()
            if not ll_disks.wait_for_disks_status(disk_name):
                raise exceptions.DiskException(
                    "Disk %s is not in the expected state 'OK" % self.disk_name
                )

    def tearDown(self):
        """
        Clean environment
        """
        if not flushIptables(self.host_ip, config.HOSTS_USER, config.HOSTS_PW):
            logger.error(
                "Failed to unblock connection from host to storage domain"
            )
            BaseTestCase.test_failed = True
        super(BasicResize, self).tearDown()


@attr(tier=2)
class TestCase5061(DisksPermutationEnvironment):
    """
    Resize virtual disk after snapshot creation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = True
    polarion_test_case = '5061'
    snap_description = 'snap_%s' % polarion_test_case

    @polarion("RHEVM3-5061")
    def test_virtual_disk_resize_after_snapshot_creation(self):
        """
        - VM with disk and OS
        - Create a snapshot to the VM
        - Resize the VM disk, add 1G to it
        """
        logger.info("Creating Snapshot")
        self.assertTrue(
            ll_vms.addSnapshot(True, self.vm_name, self.snap_description),
            "Failed to add snapshot %s" % self.snap_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)

        for disk in self.disk_names:
            logger.info("Resizing disk %s", disk)

            status = ll_vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk, provisioned_size=self.new_size
            )
            self.assertTrue(
                status, "Failed to resize disk %s to size %s"
                        % (disk, self.new_size)
            )
        if not ll_disks.wait_for_disks_status(
            self.disk_names, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )

        devices, boot_device = helpers.get_vm_storage_devices(self.vm_name)

        for device in devices:
            size = helpers.get_vm_device_size(self.vm_name, device)
            self.assertEqual(int(size), (self.new_size / config.GB))


@attr(tier=2)
class TestCase5060(DisksPermutationEnvironment):
    """
    Commit snapshot after resizing the disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = True
    polarion_test_case = '5060'
    snap_description = 'snap_%s' % polarion_test_case
    is_preview = False
    new_size = config.DISK_SIZE + config.GB
    # Bugzilla history:
    # 1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-5060")
    def test_Commit_snapshot_after_disk_resize(self):
        """
        - VM with disk and OS
        - Create a snapshot to the VM
        - Resize the VM disk, add 1G to it
        - Shutdown the VM and preview the snapshot
        - Commit the snapshot
        - The disk should have the size it was by the time we
          created the snapshot
        """
        logger.info("Creating Snapshot")
        self.assertTrue(
            ll_vms.addSnapshot(True, self.vm_name, self.snap_description),
            "Failed to add snapshot %s" % self.snap_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)

        for disk in self.disk_names:
            status = ll_vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk, provisioned_size=self.new_size
            )
            self.assertTrue(status, "Failed to resize disk %s to size %s"
                                    % (disk, self.new_size))
        if not ll_disks.wait_for_disks_status(
            self.disk_names, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disks %s is not in the expected state 'OK" % self.disk_names
            )

        status = ll_vms.preview_snapshot(
            True, self.vm_name, self.snap_description
        )
        self.is_preview = status
        self.assertTrue(
            status, "Failed to preview snapshot %s" % self.snap_description
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snap_description],
        )

        status = ll_vms.commit_snapshot(True, self.vm_name)
        self.assertTrue(
            status, "Failed restoring a previewed snapshot %s" %
                    self.snap_description
        )
        self.is_preview = not status
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)
        vm_disks = ll_vms.getVmDisks(self.vm_name)
        disks_sizes = [
            disk.get_size() for disk in vm_disks if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id())
        ]
        for size in disks_sizes:
            self.assertTrue(
                size == (self.new_size - config.GB),
                "Disk current size %s, expected size %s" %
                (size, (self.new_size - config.GB))
            )

    def tearDown(self):
        if self.is_preview:
            ll_vms.undo_snapshot_preview(True, self.vm_name)
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)

        super(TestCase5060, self).tearDown()


@attr(tier=1)
class TestCase5062(BasicResize):
    """
    Virtual disk resize - preallocated  block disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = (ISCSI in opts['storages'] or FCP in opts['storages'])
    storages = set([ISCSI, FCP])
    polarion_test_case = '5062'
    test_disk_args = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5062")
    def test_preallocated_block_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=1)
class TestCase5063(BasicResize):
    """
    Virtual disk resize - Thin block disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = (ISCSI in opts['storages'] or FCP in opts['storages'])
    storages = set([ISCSI, FCP])
    polarion_test_case = '5063'
    test_disk_args = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5063")
    def test_thin_block_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=1)
class TestCase5065(BasicResize):
    """
    Virtual disk resize - Thin file disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    # TODO: Verify it works in glusterfs and enable the test for this storage
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5065'
    test_disk_args = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5065")
    def test_thin_file_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@attr(tier=4)
class TestCase5066(BasicResize):
    """
    block connectivity from host to storage domain - preallocated disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5066'
    test_disk_args = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5066")
    def test_block_connection_preallocated_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@attr(tier=4)
class TestCase5067(BasicResize):
    """
    block connectivity from host to storage domain - sparse disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5067'
    test_disk_args = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5067")
    def test_block_connection_sparse_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@attr(tier=2)
class TestCase5069(BasicResize):
    """
    Resize shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    # glusterfs doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '5069'
    test_vm_name = "vm_%s" % polarion_test_case
    test_disk_args = {
        'sparse': False,
        'format': config.RAW_DISK,
        'shareable': True,
    }

    def setUp(self):
        """
        Creating disk
        """
        super(TestCase5069, self).setUp()
        self.test_vm_name = 'test_%s' % self.polarion_test_case
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.test_vm_name
        vm_args['storageDomainName'] = self.storage_domain

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.test_vm_name
            )
        if not ll_disks.attachDisk(True, self.disk_name, self.test_vm_name):
            raise exceptions.DiskException(
                "Failed to attach disk %s to vm %s" %
                (self.disk_name, self.test_vm_name)
            )
        if not ll_disks.wait_for_disks_status(self.disk_name):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )

    @polarion("RHEVM3-5069")
    def test_shared_block_disk_resize(self):
        """
        - 2 VM with RAW disk and OS
        - 1 shared disk
        - Resize the shared disk to 2G total
        - Check LV size on VDSM and disk size on guest of both vms
        """
        ll_vms.start_vms(
            [self.vm_name, self.test_vm_name], max_workers=2, wait_for_ip=False
        )
        names = "%s, %s" % (self.vm_name, self.test_vm_name)
        if not ll_vms.waitForVmsStates(True, names):
            raise exceptions.VMException(
                "VMs %s is not in desired state: 'OK'", names)
        self.perform_basic_action()
        devices, boot_device = (
            helpers.get_vm_storage_devices(self.test_vm_name)
        )
        for device in devices:
            size = helpers.get_vm_device_size(self.test_vm_name, device)
            self.assertEqual(int(size), int(self.new_size / config.GB))

    def tearDown(self):
        if not ll_vms.safely_remove_vms([self.test_vm_name, self.vm_name]):
            logger.error(
                "Failed to power off and remove vms %s",
                ', '.join([self.test_vm_name, self.vm_name])
            )
            BaseTestCase.test_failed = True
        if not ll_disks.deleteDisk(True, self.disk_name):
            logger.error("Failed to delete disk %s", self.disk_name)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5070(BasicResize):
    """
    Extend disk to more than available capacity
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])

    polarion_test_case = '5070'
    test_disk_args = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    def setUp(self):
        """
        Creating disk
        """
        super(TestCase5070, self).setUp()
        storage_domain_size = ll_sds.get_total_size(self.storage_domain)
        self.new_size = (config.DISK_SIZE + config.GB * storage_domain_size)

    @polarion("RHEVM3-5070")
    def test_thin_block_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to disk current size + total storage domain size
        """
        logger.info("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            False, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        self.assertTrue(
            status, "Succeeded to resize disk %s to new size %s"
                    % (self.disk_name, self.new_size)
        )

    def tearDown(self):
        if not ll_disks.wait_for_disks_status(self.disk_name):
            logger.error(
                "Disk %s is not in the expected state 'OK", self.disk_name
            )
            BaseTestCase.test_failed = True
        super(TestCase5070, self).tearDown()


@attr(tier=4)
class TestCase5071(BasicResize):
    """
    Stop libvirt service during disk extension
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = True
    polarion_test_case = '5071'
    look_for_regex = 'Run and protect: extendVolumeSize'

    test_disk_args = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5071")
    def test_stop_libvirt_during_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - When SPM get The task, stop libvirt service
        """
        self.host = ll_hosts.getSPMHost(config.HOSTS)
        host_ip = ll_hosts.getHostIP(self.host)
        t = Thread(target=watch_logs, args=(
            config.VDSM_LOG, self.look_for_regex, self.stop_libvirt, None,
            host_ip, config.HOSTS_USER, config.HOSTS_PW))
        t.start()

        time.sleep(5)

        logger.info("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            True, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        t.join()
        self.assertTrue(
            status, "Failed to resize disk %s to size %s"
                    % (self.disk_name, self.new_size)
        )
        host_machine = Machine(
            host=host_ip, user=config.HOSTS_USER,
            password=config.HOSTS_PW
        ).util('linux')
        rc, output = host_machine.runCmd(self.start_libvirt.split())
        self.assertTrue(rc, "Failed to start libvirt: %s" % output)
        if not ll_disks.wait_for_disks_status(
            self.disk_name, timeout=DISK_RESIZE_TIMEOUT
        ):
            logger.error(
                "Disk %s is not in the expected state 'OK", self.disk_name
            )
        logger.info("dd to disk %s", self.disk_name)
        storage_helpers.perform_dd_to_disk(self.vm_name, self.disk_name)
        logger.info("Getting volume size")

        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [
            disk_obj for disk_obj in disks_objs if not
            ll_vms.is_bootable_disk(self.vm_name, disk_obj.get_id())
        ][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        lv_size = helpers.get_volume_size(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, disk_obj,
            datacenter_obj
        )
        self.assertEqual(lv_size, self.new_size / config.GB)


@attr(tier=2)
class TestCase5073(BasicResize):
    """
    Increase and decrease multiple disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5073'
    vm_name = "vm_%s_%s"
    vm_count = 3
    new_size = (config.VM_DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating disk
        """
        self.vm_names = list()
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['installation'] = False

        logger.info('Creating vm and installing OS on it')

        for i in range(self.vm_count):
            self.vm_name = "vm_%s_%s_%s" % (
                self.polarion_test_case, self.storage, i)
            vm_args['vmName'] = self.vm_name
            if not storage_helpers.create_vm_or_clone(**vm_args):
                raise exceptions.VMException(
                    'Unable to create vm %s for test' % self.vm_name
                )
            self.vm_names.append(self.vm_name)

    @polarion("RHEVM3-5073")
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
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error(
                "Failed to power off and remove vms: %s", ', '.join(
                    self.vm_names
                )
            )
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase11862(BasicResize):
    """
    Increase and decrease multiple disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '11862'
    vm_name = "vm_%s_%s"
    vm_count = 2
    new_size = (config.VM_DISK_SIZE + config.GB)

    def setUp(self):
        """
        Creating disk
        """
        self.vm_names = list()
        vm_args = config.create_vm_args.copy()
        vm_args['installation'] = False

        logger.info('Creating vm')
        sd_list = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0:1]

        for i, sd in zip(range(self.vm_count), sd_list):
            self.vm_name = "vm_%s_%s"
            vm_args['storageDomainName'] = sd
            self.vm_name = self.vm_name % (self.polarion_test_case, i)
            vm_args['vmName'] = self.vm_name
            if not storage_helpers.create_vm_or_clone(**vm_args):
                raise exceptions.VMException('Unable to create vm %s for test'
                                             % self.vm_name)
            self.vm_names.append(self.vm_name)

    @polarion("RHEVM3-11862")
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
        if not ll_vms.safely_remove_vms(self.vm_names):
            BaseTestCase.test_failed = True
            logger.error(
                "Failed to power off and remove VMs '%s'", ', '.join(
                    self.vm_names
                )
            )
        BaseTestCase.teardown_exception()
