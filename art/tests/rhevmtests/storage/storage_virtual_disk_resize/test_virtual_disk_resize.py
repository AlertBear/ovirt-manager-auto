"""
3.3 Feature: Storage Virtual disk resize
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Virtual_Disk_Resize
"""
import config
from config import (
    NFS,
    GLUSTER,
    ISCSI,
    CEPH,
    FCP,
)
import helpers
import logging
import pytest
import time
import shlex
from threading import Thread
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
    storages,
)
from art.unittest_lib.common import StorageTest as BaseTestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dcs,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sds,
    vms as ll_vms
)
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.utils.log_listener import watch_logs
from art.test_handler import exceptions
from art.test_handler.tools import polarion, bz

from rhevmtests.storage.fixtures import (
    create_vm, create_snapshot, add_disk, attach_disk,
    initialize_storage_domains, poweroff_vm, add_disk_permutations,
    attach_and_activate_disks, delete_disk, start_vm,
    init_host_or_engine_executor
)

from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    initialize_attributes, wait_for_disks_status_ok,
    create_multiple_vms, add_vm_with_disk, flush_ip_table
)

logger = logging.getLogger(__name__)

DISK_RESIZE_TIMEOUT = 1200
WATCH_TIMOUT = 480


class BasicResize(BaseTestCase):
    """
    A class with common methods
    """
    new_size = (config.DISK_SIZE + config.GB)
    block_cmd = "iptables -I OUTPUT -d %s -p tcp -j DROP"
    stop_libvirt = "service libvirtd stop"
    start_libvirt = "service libvirtd start"
    add_disk_params = {}

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
            self.vm_name, self.disk_name, size=dd_size, write_to_file=True
        )
        testflow.step(
            "Performing 'dd' command to extended disk %s", self.disk_name
        )
        assert ecode, "dd command failed. output: %s" % output
        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [disk_obj for disk_obj in disks_objs if
                    (self.disk_name == disk_obj.get_alias())][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        testflow.step(
            "Checking volume size for disk %s in host %s ",
            disk_obj.get_alias(), self.host
        )
        lv_size = helpers.get_volume_size(
            self.host, disk_obj, datacenter_obj, size_format='m'
        )
        assert not lv_size == -1
        EXPECTED_THRESHOLD = 50 * config.MB
        assert (
            ((self.new_size/config.MB) - lv_size) < EXPECTED_THRESHOLD
        ), (
            "Disk extended to size %s, real size %s was not close to the "
            "threshold %s MB" % (
                self.new_size/config.MB, lv_size, EXPECTED_THRESHOLD
            )
        )
        devices, boot_device = helpers.get_vm_storage_devices(self.vm_name)

        for device in devices:
            size = helpers.get_vm_device_size(self.vm_name, device)
            assert int(size) == (self.new_size / config.GB)

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

        testflow.step("Resizing disk %s", self.disk_name)
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
        testflow.step("Unblocking the connection to host %s", self.host_ip)
        storage_helpers.flushIptables(
            self.host_ip,
            config.HOSTS_USER,
            config.HOSTS_PW
        )
        if not ll_disks.wait_for_disks_status(
            self.disk_name, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disk %s is not in the expected state 'OK" % self.disk_name
            )
        ll_hosts.wait_for_hosts_states(True, self.host)

        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [
            disk_obj for disk_obj in disks_objs if not
            ll_vms.is_bootable_disk(self.vm_name, disk_obj.get_id())
        ][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        testflow.step("Check volume size for disk %s", disk_obj.get_alias())
        lv_size = helpers.get_volume_size(
            self.host_ip, disk_obj, datacenter_obj
        )
        assert not lv_size == -1
        assert lv_size == self.new_size / config.GB
        devices, boot_device = helpers.get_vm_storage_devices(self.vm_name)
        ll_vms.start_vms([self.vm_name], max_workers=1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)
        for device in devices:
            size = helpers.get_vm_device_size(self.vm_name, device)
            assert int(size) == (self.new_size / config.GB)

    def multiple_disks(self, vm_names):
        """
        Extend multiple disks
        """
        for vm in vm_names:
            disk_name = ll_vms.getVmDisks(vm)[0].get_alias()
            testflow.step("Resizing disk %s", disk_name)
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
                    "Disk %s is not in the expected state 'OK" % disk_name
                )


@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    add_disk_permutations.__name__,
    attach_and_activate_disks.__name__,
    create_snapshot.__name__,
)
class TestCase5061(BaseTestCase):
    """
    Resize virtual disk after snapshot creation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    new_size = (config.DISK_SIZE + config.GB)

    @polarion("RHEVM3-5061")
    @tier3
    def test_virtual_disk_resize_after_snapshot_creation(self):
        """
        - VM with disk and OS
        - Create a snapshot to the VM
        - Resize the VM disk, add 1G to it
        """
        for disk in self.disk_names:
            testflow.step("Resizing disk %s", disk)

            status = ll_vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk, provisioned_size=self.new_size
            )
            assert status, "Failed to resize disk %s to size %s" % (
                disk, self.new_size
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
            assert int(size) == (self.new_size / config.GB)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk_permutations.__name__,
    attach_and_activate_disks.__name__,
    create_snapshot.__name__,
)
class TestCase5060(BaseTestCase):
    """
    Commit snapshot after resizing the disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    is_preview = False
    new_size = config.DISK_SIZE + config.GB

    @polarion("RHEVM3-5060")
    @tier3
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
        for disk in self.disk_names:
            testflow.step("Resizing disk %s", disk)
            status = ll_vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk, provisioned_size=self.new_size
            )
            assert status, "Failed to resize disk %s to size %s" % (
                disk, self.new_size
            )
        if not ll_disks.wait_for_disks_status(
            self.disk_names, timeout=DISK_RESIZE_TIMEOUT
        ):
            raise exceptions.DiskException(
                "Disks %s is not in the expected state 'OK" % self.disk_names
            )

        testflow.step("Preview snapshot on VM %s", self.vm_name)
        status = ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )
        self.is_preview = status
        assert status, (
            "Failed to preview snapshot %s" % self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )

        testflow.step("Commit snapshot on VM %s", self.vm_name)
        status = ll_vms.commit_snapshot(True, self.vm_name)
        assert status, "Failed restoring a previewed snapshot %s" % (
            self.snapshot_description
        )
        self.is_preview = not status
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(self.vm_name)
        vm_disks = ll_vms.getVmDisks(self.vm_name)
        disks_sizes = [
            disk.get_provisioned_size() for disk in vm_disks if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id())
        ]
        testflow.step("Check VM %s disk sizes", self.vm_name)
        for size in disks_sizes:
            assert size == (
                self.new_size - config.GB
            ), "Disk current size %s, expected size %s" % (
                size, self.new_size - config.GB
            )


@storages((ISCSI, FCP))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5062(BasicResize):
    """
    Virtual disk resize - preallocated  block disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5062")
    @tier1
    @bz({'1408594': {}})
    def test_preallocated_block_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@storages((ISCSI, FCP))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5063(BasicResize):
    """
    Virtual disk resize - Thin block disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5063")
    @tier1
    @bz({'1408594': {}})
    def test_thin_block_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check LV size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@storages((GLUSTER, CEPH, NFS))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5065(BasicResize):
    """
    Virtual disk resize - Thin file disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5065")
    @tier1
    def test_thin_file_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Send IOs to disk
        - Check size on VDSM and disk size on guest
        """
        self.perform_basic_action()


@storages((ISCSI,))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    flush_ip_table.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5066(BasicResize):
    """
    block connectivity from host to storage domain - preallocated disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5066")
    @tier4
    def test_block_connection_preallocated_resize(self):
        """
        - VM with preallocated disk and OS
        - Resize the VM disk to 2G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@storages((ISCSI,))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    flush_ip_table.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5067(BasicResize):
    """
    block connectivity from host to storage domain - sparse disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5067")
    @tier4
    def test_block_connection_sparse_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - Block connection from host to storage after lvextend
        - restore connection
        - Check LV size on VDSM and disk size on guest
        """
        self.block_connection_case()


@storages((NFS, ISCSI))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    delete_disk.__name__,
    attach_disk.__name__,
    add_vm_with_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5069(BasicResize):
    """
    Resize shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    # glusterfs doesn't support shareable disks
    add_disk_params = {
        'sparse': False,
        'format': config.RAW_DISK,
        'shareable': True,
    }

    @polarion("RHEVM3-5069")
    @tier2
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
            assert int(size) == int(self.new_size / config.GB)


@storages((ISCSI,))
@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    wait_for_disks_status_ok.__name__,
    poweroff_vm.__name__,
)
class TestCase5070(BasicResize):
    """
    Extend disk to more than available capacity
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    add_disk_params = {
        'sparse': False,
        'format': config.RAW_DISK,
    }

    @polarion("RHEVM3-5070")
    @tier2
    def test_thin_block_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to disk current size + total storage domain size
        """
        storage_domain_size = ll_sds.get_total_size(
            self.storage_domain, config.DATA_CENTER_NAME
        )
        self.new_size = (config.DISK_SIZE + config.GB * storage_domain_size)
        testflow.step("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            False, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        assert status, "Succeeded to resize disk %s to new size %s" % (
            self.disk_name, self.new_size
        )


@pytest.mark.usefixtures(
    init_host_or_engine_executor.__name__,
    create_vm.__name__,
    start_vm.__name__,
    initialize_attributes.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase5071(BasicResize):
    """
    Stop libvirt service during disk extension
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    look_for_regex = 'START extendVolumeSize'

    add_disk_params = {
        'sparse': True,
        'format': config.COW_DISK,
    }

    @polarion("RHEVM3-5071")
    @tier4
    def test_stop_libvirt_during_resize(self):
        """
        - VM with thin disk and OS
        - Resize the VM disk to 2G total
        - When SPM get The task, stop libvirt service
        """
        self.host = ll_hosts.get_spm_host(config.HOSTS)
        host_ip = ll_hosts.get_host_ip(self.host)
        t = Thread(target=watch_logs, args=(
            config.VDSM_LOG, self.look_for_regex, self.stop_libvirt, None,
            host_ip, config.HOSTS_USER, config.HOSTS_PW))
        t.start()

        time.sleep(5)

        testflow.step("Resizing disk %s", self.disk_name)
        status = ll_vms.extend_vm_disk_size(
            True, self.vm_name, disk=self.disk_name,
            provisioned_size=self.new_size
        )
        t.join()
        assert status, "Failed to resize disk %s to size %s" % (
            self.disk_name, self.new_size
        )
        rc, out, err = shlex.split(self.executor.run_cmd(self.start_libvirt))
        assert not rc, "Failed to start libvirt: %s" % err
        if not ll_disks.wait_for_disks_status(
            self.disk_name, timeout=DISK_RESIZE_TIMEOUT
        ):
            logger.error(
                "Disk %s is not in the expected state 'OK", self.disk_name
            )
        logger.info("dd to disk %s", self.disk_name)

        if self.storage in config.BLOCK_TYPES:
            dd_size = self.new_size - 600 * config.MB
        else:
            dd_size = self.new_size

        testflow.step("Writing data to disk %s", self.disk_name)
        storage_helpers.perform_dd_to_disk(
            self.vm_name, self.disk_name, size=dd_size
        )
        logger.info("Getting volume size")

        disks_objs = ll_vms.getVmDisks(self.vm_name)
        disk_obj = [
            disk_obj for disk_obj in disks_objs if not
            ll_vms.is_bootable_disk(self.vm_name, disk_obj.get_id())
        ][0]
        datacenter_obj = ll_dcs.get_data_center(config.DATA_CENTER_NAME)

        lv_size = helpers.get_volume_size(self.host, disk_obj, datacenter_obj)
        assert not lv_size == -1
        assert lv_size == self.new_size / config.GB


@storages((ISCSI,))
@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_multiple_vms.__name__,
)
class TestCase5073(BasicResize):
    """
    Increase and decrease multiple disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    multiple_sd = False
    vm_count = 3
    new_size = 20 * config.GB

    @polarion("RHEVM3-5073")
    @tier2
    def test_multiple_disks_resize_same_SD(self):
        """
        - 5 vms with OS, disks on same SD
        - resize the first 3 virtual disks to 20G (increase size)
        - resize the 2 left disks to 10G (decrease size) (NOT supported)
        - all resizing tasks should run together (as possible) without waiting
          for tasks to complete.
        """
        self.multiple_disks(self.vm_names)


@storages((ISCSI,))
@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_multiple_vms.__name__,
)
class TestCase11862(BasicResize):
    """
    Increase and decrease multiple disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Virtual_Disk_Resize
    """
    vm_count = 2
    multiple_sd = True
    new_size = 20 * config.GB

    @polarion("RHEVM3-11862")
    @tier2
    def test_multiple_disks_resize_different_SD(self):
        """
        - 5 vms with OS, disks on different SD
        - resize the first 3 virtual disks to 20G (increase size)
        - resize the 2 left disks to 10G (decrease size) (NOT supported)
        - all resizing tasks should run together (as possible) without waiting
          for tasks to complete.
        """
        self.multiple_disks(self.vm_names)
