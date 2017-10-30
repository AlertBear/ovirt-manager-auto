"""
4.0 Storage ability to change disk interface for a VM disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/4_0_Storage_Ability_to_change_disk_interface_for_a_VM_disk
"""
import re
import config
import logging
import pytest
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
)
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.storage_disk_image_format.fixtures import (
    create_second_vm, create_disks_to_vm, create_disks_to_vm_by_interface,
)
from rhevmtests.storage.fixtures import (
    create_vm, add_disk, update_vm, delete_disk, attach_disk
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)

INTERFACE_REGEX_GUEST_OS = {
    config.INTERFACE_VIRTIO: "vd[a-z]",
    config.INTERFACE_VIRTIO_SCSI: "sd[a-z]",
    config.INTERFACE_SPAPR_VSCSI: "sd[a-z]",
    config.INTERFACE_IDE: "sd[a-z]",
}


class BaseTestCase(TestCase):

    disk_id = None

    def check_engine_disk_interface(
        self, disk_interface, vm_name=None, disk_id=None
    ):
        if not vm_name:
            vm_name = self.vm_name
        if not disk_id:
            disk_id = self.disk_id
        disk = ll_vms.get_disk_attachment(vm_name, disk_id)
        assert disk_interface == disk.get_interface(), (
            "Disk %s should have interface %s instead interface is %s"
            % (disk_id, disk_interface, disk.get_interface())
        )

    def check_guest_os_disk_interface(
        self, interface, vm_name=None, disk_id=None
    ):
        if not vm_name:
            vm_name = self.vm_name
        if not disk_id:
            disk_id = self.disk_id
        vm_status = ll_vms.get_vm_state(vm_name)
        vm_started = False
        if vm_status != config.VM_UP:
            testflow.step("Start VM %s", vm_name)
            ll_vms.startVm(
                positive=True, vm=vm_name, wait_for_status=config.VM_UP,
                wait_for_ip=True
            )
            vm_started = True
        logical_name = ll_vms.get_vm_disk_logical_name(
            vm_name, disk_id, key='id',
            parse_logical_name=True
        )
        assert re.match(
            INTERFACE_REGEX_GUEST_OS[interface],
            logical_name
        ), "Interface %s does not match expected pattern %s" % (
            logical_name, INTERFACE_REGEX_GUEST_OS[interface]
        )
        if vm_started:
            status_action = {
                config.VM_DOWN: "shutdown",
                config.VM_PAUSED: "pause",
            }
            ll_vms.changeVMStatus(
                True, vm_name, status_action[vm_status],
                vm_status, async='false'
            )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_disks_to_vm_by_interface.__name__,
)
class TestCaseMultipleDisks(BaseTestCase):

    disk_aliases = []

    def get_iteration(self, interface):
        """
        Return a new interface to test from the remaining interfaces
        """
        combination = filter(lambda w: w[0] == interface, self.permutations)
        if not combination:
            return None
        self.permutations.remove(combination[0])
        return combination[0][1]

    def change_vm_disks_interfaces(self, positive=True, check_guest=True):
        """
        While there exist permutation to test, change the interface of
        the disk and check RHEVM and the guest OS for the interface change
        """
        while self.permutations:
            map_change = []
            for disk in ll_vms.get_disk_attachments(self.vm_name):
                if disk.get_bootable():
                    continue
                previous_interface = disk.get_interface()
                new_interface = self.get_iteration(previous_interface)
                if not new_interface:
                    continue
                testflow.step(
                    "Update disk %s interface to %s", disk,
                    new_interface
                )
                status = ll_disks.updateDisk(
                    True, vmName=self.vm_name, id=disk.get_id(),
                    interface=new_interface
                )
                assert positive == status, (
                    "Changing disk %s interface from %s to %s %s " %
                    (
                        disk.get_id(), previous_interface, new_interface,
                        'failed' if positive else 'passed'
                    )
                )
                logger.info(
                    "Disk %s changed interface from %s to %s %s",
                    disk.get_id(), previous_interface, new_interface,
                    'passed' if positive else 'failed'
                )
                map_change.append(
                    (
                        disk.get_id(),
                        new_interface if positive else previous_interface
                    )
                )

            for disk_id, new_interface in map_change:
                self.check_engine_disk_interface(
                    new_interface, disk_id=disk_id
                )

            if not check_guest:
                continue

            vm_status = ll_vms.get_vm_state(self.vm_name)
            if vm_status != config.VM_UP:
                testflow.step("Start VM %s", self.vm_name)
                ll_vms.startVm(
                    True, self.vm_name, config.VM_UP, wait_for_ip=True
                )
                for disk_id, new_interface in map_change:
                    self.check_guest_os_disk_interface(
                        new_interface, disk_id=disk_id
                    )

                status_action = {
                    config.VM_DOWN: "shutdown",
                    config.VM_PAUSED: "pause",
                }
                ll_vms.changeVMStatus(
                    True, self.vm_name, status_action[vm_status],
                    vm_status, async='false'
                )


class TestCase14943(TestCaseMultipleDisks):
    """
    RHEVM-14943 - Change disk interface

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14943
    """
    __test__ = True

    @polarion("RHEVM-14943")
    @tier2
    def test_change_disk_interface(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create 2 disks and attach them to the VM (VirtIO and VirtIO-SCSI)
        Test flow:
        - While the VM is stopped change disk interface
        (From VirtIO to VirtioIO-SCSI and viceversa) -> Should succeed
        - Check the disks interface in RHEVM and in the guest OS ->
        Disks interface should get changed in RHEVM and in the guest
        """
        self.change_vm_disks_interfaces()


class TestCase14944(TestCaseMultipleDisks):
    """
    RHEVM-14944 Change disk interface - Direct LUN

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14944
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([config.STORAGE_TYPE_ISCSI])
    lun_disks = True

    @polarion("RHEVM-14944")
    @tier2
    def test_change_disk_interface_direct_lun(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create 2 direct LUN disks and attach them to the VM
        (VirtIO and VirtIO-SCSI)

        Test flow:
        - While the VM is stopped change disk interface
        (From VirtIO to VirtioIO-SCSI and viceversa) -> Should be possible
        to change the disks interface while the VM is not running
        - Check the disks interface in RHEVM and in the guest OS ->
        Disks interface should get changed in RHEVM and in the guest
        """
        self.change_vm_disks_interfaces(check_guest=False)


@pytest.mark.usefixtures(
    delete_disk.__name__,
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__
)
class BaseOneDiskAttachedTestCase(BaseTestCase):

    base_interface = config.INTERFACE_VIRTIO
    new_interface = config.INTERFACE_VIRTIO_SCSI
    add_disk_params = {
        'interface': base_interface
    }

    def update_disk_interface(self, positive=True, check_guest=True):
        """
        Update the disk interface to new_interface and assert the result
        according to postivie
        """
        self.disk_id = ll_disks.get_disk_obj(self.disk_name).get_id()
        testflow.step(
            "Update disk %s interface to %s", self.disk_name,
            self.new_interface
        )
        status = ll_disks.updateDisk(
            positive=positive, vmName=self.vm_name, alias=self.disk_name,
            interface=self.new_interface
        )
        assert status, "Changing disk %s interface from %s to %s %s " % (
            self.disk_name, self.base_interface, self.new_interface,
            'failed' if positive else 'passed'
        )
        logger.info(
            "Disk %s changed interface from %s to %s %s",
            self.disk_name, self.base_interface, self.new_interface,
            'passed' if positive else 'failed'
        )
        if positive:
            expected_interface = self.new_interface
        else:
            expected_interface = self.base_interface

        self.check_engine_disk_interface(expected_interface)

        if positive and check_guest:
            self.check_guest_os_disk_interface(expected_interface)


@pytest.mark.usefixtures(
    delete_disk.__name__,
    create_vm.__name__,
    create_second_vm.__name__,
    add_disk.__name__,
)
class TestCase14945(BaseTestCase):
    """
    RHEVM-14945 - Shared disk attached to serveral VMs with different
    interface types

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-6245
    """
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_FCP in ART_CONFIG['RUN']['storages']
    )
    storages = set([
        config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS,
        config.STORAGE_TYPE_FCP
    ])
    add_disk_params = {
        'shareable': True,
        'format': config.RAW_DISK,
        'sparse': False,
        'interface': config.INTERFACE_IDE
    }

    @polarion("RHEVM-14945")
    @tier2
    def test_shared_disk_different_interfaces(self):
        """
        Test setup:
        - Create 2 VMs with disk attached and install OS
        - Create a floating shared disk

        Test flow:
        - Attach the shared disk to each VM - one as VirtIO and one as
        VirtIO-SCSI
        - Check the disks interface in RHEVM and in the guest OS
        -> Disk in the guest OS should be the one set in RHEVM
        - Change the shared disk interface -> Disks interface should get
        changed in RHEVM and in the guest for the specific VM ONLY
        """
        self.vm_names = [self.vm_name, self.vm_name_2]
        self.disk_id = ll_disks.get_disk_obj(self.disk_name).get_id()
        testflow.step(
            "Attach and activate  disk %s to VM %s", self.vm_names[0],
            self.disk_name
        )
        assert ll_disks.attachDisk(
            positive=True, alias=self.disk_name, vm_name=self.vm_names[0],
            active=False, disk_id=self.disk_id,
            interface=config.INTERFACE_IDE
        )
        assert ll_vms.activateVmDisk(
            positive=True, vm=self.vm_names[0], diskId=self.disk_id
        )
        testflow.step(
            "Attach and Activate disk %s to VM %s", self.vm_names[1],
            self.disk_name
        )
        assert ll_disks.attachDisk(
            positive=True, alias=self.disk_name, vm_name=self.vm_names[1],
            active=False, disk_id=self.disk_id,
            interface=config.INTERFACE_VIRTIO
        )
        assert ll_vms.activateVmDisk(
            positive=True, vm=self.vm_names[1], diskId=self.disk_id
        )
        testflow.step("Start VMs %s", self.vm_names)
        ll_vms.start_vms(self.vm_names, wait_for_ip=True)
        self.check_engine_disk_interface(
            config.INTERFACE_IDE, self.vm_names[0]
        )
        self.check_engine_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[1]
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_IDE, self.vm_names[0]
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[1]
        )
        testflow.step("Stop VMs %s", self.vm_names)
        ll_vms.stop_vms_safely(self.vm_names)
        testflow.step(
            "Update disk %s interface to %s in VM %s", self.disk_name,
            config.INTERFACE_VIRTIO, self.vm_names[0]
        )
        assert ll_disks.updateDisk(
            positive=True, vmName=self.vm_names[0], alias=self.disk_name,
            interface=config.INTERFACE_VIRTIO
        )
        testflow.step(
            "Update disk %s interface to %s in VM %s", self.disk_name,
            config.INTERFACE_IDE, self.vm_names[1]
        )
        assert ll_disks.updateDisk(
            True, vmName=self.vm_names[1], alias=self.disk_name,
            interface=config.INTERFACE_IDE
        )
        testflow.step("Start VMs %s", self.vm_names)
        ll_vms.start_vms(self.vm_names, wait_for_ip=True)
        self.check_engine_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[0], self.disk_id
        )
        self.check_engine_disk_interface(
            config.INTERFACE_IDE, self.vm_names[1], self.disk_id
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[0], self.disk_id
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_IDE, self.vm_names[1], self.disk_id
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_disks_to_vm.__name__,
)
class TestCase14946(BaseTestCase):
    """
    RHEVM-14946 - Change disks to IDE for a large number of PCI devices

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14946
    """
    # Gluster doesn't support IDE interface
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_FCP in ART_CONFIG['RUN']['storages']
    )
    storages = set([
        config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS,
        config.STORAGE_TYPE_FCP
    ])

    @polarion("RHEVM-14946")
    @tier3
    def test_change_disk_ide_large_number_devices(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create and attach 4 disks to the VM with VirtIO interface

        Test flow:
        - While the VM is stopped, change all the disks interface to IDE ->
        Should fail, It shouldn't be allowed to have more than 3 IDE disks
        attached to the VM
        """
        for disk in self.disk_aliases[:3]:
            testflow.step(
                "Update disk %s interface to %s", disk, config.INTERFACE_IDE
            )
            assert ll_disks.updateDisk(
                True, vmName=self.vm_name, alias=disk,
                interface=config.INTERFACE_IDE
            ), "Error changing disk interface to IDE"
        testflow.step(
            "Update disk %s interface to %s", self.disk_aliases[3],
            config.INTERFACE_IDE
        )
        assert ll_disks.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_aliases[3],
            interface=config.INTERFACE_IDE
        ), (
            "It shouldn't be possible to have more than 3 disks with "
            "interface IDE attached to a VM"
        )


class TestCase14947(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14947 - Negative - Try to change disk interface attach to a running
    VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14947
    """
    __test__ = True

    @polarion("RHEVM-14947")
    @tier3
    def test_change_disk_running_vm(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create and attach a disk to the VM

        Test flow:
        - Start the VM
        - Try to change the disk interface of the attached disk while the VM is
        running -> Should fail
        """
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        self.update_disk_interface(positive=False)


@pytest.mark.usefixtures(
    delete_disk.__name__,
    create_vm.__name__,
    add_disk.__name__,
)
class TestCase14948(BaseTestCase):
    """
    RHEVM_14948 - Negative - Try to attach disk to a VM without the interface
    parameter set

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14948
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_FCP in ART_CONFIG['RUN']['storages']
    )
    storages = set([
        config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS,
        config.STORAGE_TYPE_FCP
    ])
    add_disk_params = {
        'shareable': True,
        'format': config.RAW_DISK,
        'sparse': False,
        'interface': config.INTERFACE_IDE
    }

    @polarion("RHEVM-14948")
    @tier3
    def test_attach_disk_without_interface(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create a shared disk

        Test flow:
        - Attach the shared disk to the VM and don't specify the interface
        type -> Should fail
        """
        disk_obj = ll_disks.get_disk_obj(self.disk_name)
        testflow.step(
            "Attach disk %s to VM %s without interface", self.disk_name,
            self.vm_name
        )
        assert ll_disks.attachDisk(
            positive=False, alias=self.disk_name,
            vm_name=self.vm_name, active=False, disk_id=disk_obj.get_id(),
            interface=None
        ), (
            "Succeeded to attach a disk to a VM without specifying "
            "the disk interface"
        )


class TestCase14949(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14949 - Disk interface after restore snapshot

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14949
    """
    __test__ = True

    @polarion("RHEVM-14949")
    @tier3
    def test_change_disk_and_restore_snapshot(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create and attach a disk to the VM with Virtio interface

        Test flow:
        - Create a snapshot
        - Try to change the disk interface of the attached disk to Virtio-SCSI
        -> Should succeed
        - Restore the snapshot in the previous step
        - Start the VM -> The disk interface should get changed back to Virtio
        in the RHEVM engine and in the guest OS
        """
        self.snapshot_name = "snapshot_update_disk"
        testflow.step(
            "Add snapshot %s to VM %s", self.snapshot_name, self.vm_name
        )
        assert ll_vms.addSnapshot(True, self.vm_name, self.snapshot_name)
        self.update_disk_interface()
        assert ll_vms.stop_vms_safely([self.vm_name])
        testflow.step(
            "Restore VM %s to snapshot %s", self.vm_name, self.snapshot_name
        )
        assert ll_vms.restore_snapshot(True, self.vm_name, self.snapshot_name)
        self.check_engine_disk_interface(self.base_interface)
        self.check_guest_os_disk_interface(self.base_interface)


class TestCase14955(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14955 - Change disk interface for a suspended VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14955
    """
    __test__ = True

    @polarion("RHEVM-14955")
    @tier3
    def test_change_disk_suspended_vm(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create and attach a disk to the VM

        Test flow:
        - Start the VM
        - Suspend the VM
        - Try to change the disk interface of the attached disk to Virtio-SCSI
        -> Should fail
        """
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        testflow.step("Suspend VM %s", self.vm_name)
        ll_vms.suspendVm(True, self.vm_name)
        self.update_disk_interface(positive=False)


@pytest.mark.usefixtures(
    delete_disk.__name__,
    create_vm.__name__,
    update_vm.__name__,
    add_disk.__name__
)
class TestCase16716(TestCase):
    """
    Attach a disk to a VM with virtio-scsi interface when the VM does not
    support that interface
    """
    __test__ = True
    installation = False
    update_vm_params = {
        "virtio_scsi": False
    }

    @polarion("RHEVM-16716")
    @tier3
    def test_attach_virtio_scsi_disk_to_unsupported_vm(self):
        """
        Attach a disk to a VM when the interface is virtio-scsi and the VM does
        not support this interface
        """
        testflow.step("Attach disk %s to VM %s", self.disk_name, self.vm_name)
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, interface=config.VIRTIO_SCSI
        ), "Succeeded to attach disk %s to VM %s" % (
            self.disk_name, self.vm_name
        )
