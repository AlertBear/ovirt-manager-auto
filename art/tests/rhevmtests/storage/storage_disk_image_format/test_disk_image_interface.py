"""
4.0 Storage ability to change disk interface for a VM disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/4_0_Storage_Ability_to_change_disk_interface_for_a_VM_disk
"""
import re
import config
import itertools
import logging
import pytest

from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    create_vm, add_disk, update_vm
)

ENUMS = config.ENUMS

logger = logging.getLogger(__name__)

TEST_INTERFACES = (
    config.INTERFACE_VIRTIO, config.INTERFACE_VIRTIO_SCSI
)

if config.PPC_ARCH:
    TEST_INTERFACES = (
        config.INTERFACE_VIRTIO, config.INTERFACE_VIRTIO_SCSI,
        config.INTERFACE_SPAPR_VSCSI
    )

INTERFACE_REGEX_GUEST_OS = {
    config.INTERFACE_VIRTIO: "vd[a-z]",
    config.INTERFACE_VIRTIO_SCSI: "sd[a-z]",
    config.INTERFACE_SPAPR_VSCSI: "sd[a-z]",
    config.INTERFACE_IDE: "sd[a-z]",
}


class BaseTestCase(TestCase):

    def create_vm_setup(self):
        """
        Create a vm
        """
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        vm_args_copy = config.create_vm_args.copy()
        vm_args_copy['vmName'] = self.vm_name
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        vm_args_copy['storageDomainName'] = self.storage_domain
        if not storage_helpers.create_vm_or_clone(**vm_args_copy):
            raise exceptions.VMException(
                "Unable to create vm %s" % self.vm_name
            )

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
            ll_vms.startVm(
                True, vm_name, config.VM_UP, wait_for_ip=True
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

    def finalizer_BaseTestCase(self):
        """
        Remove created vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            TestCase.test_failed = True
            logger.error("Failed to remove vm %s", self.vm_name)
        BaseTestCase.teardown_exception()


class TestCaseMultipleDisks(BaseTestCase):

    @pytest.fixture(scope='function')
    def initializer_TestCaseMultipleDisks_fixture(
        self, request
    ):
        """
        Create fixture
        """
        request.addfinalizer(self.finalizer_BaseTestCase)
        self.initializer_TestCaseMultipleDisks()

    def initializer_TestCaseMultipleDisks(self):
        """
        Create a vm and as many disks as interfaces to test and attach them
        to the vm
        """
        self.permutations = (
            filter(
                lambda w: w[0] != w[1],
                itertools.permutations(TEST_INTERFACES, 2)
            )
        )
        self.create_vm_setup()
        self.disk_aliases = []
        for disk_interface in TEST_INTERFACES:
            disk_args = config.disk_args.copy()
            disk_args['interface'] = disk_interface
            disk_args['alias'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
            disk_args['wait'] = False
            disk_args['storagedomain'] = self.storage_domain
            if not ll_vms.addDisk(True, self.vm_name, **disk_args):
                raise exceptions.DiskException(
                    "Unable to create disk %s" % disk_args['alias']
                )
            self.disk_aliases.append(disk_args['alias'])

        if not ll_disks.wait_for_disks_status(self.disk_aliases):
            raise exceptions.DiskException(
                "Failed to wait for disk %s status OK" % self.disk_aliases
            )

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


@attr(tier=2)
class TestCase14943(TestCaseMultipleDisks):
    """
    RHEVM-14943 - Change disk interface

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14943
    """
    __test__ = True

    @polarion("RHEVM-14943")
    @pytest.mark.usefixtures("initializer_TestCaseMultipleDisks_fixture")
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


@attr(tier=2)
class TestCase14944(TestCaseMultipleDisks):
    """
    RHEVM-14944 Change disk interface - Direct LUN

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14944
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    storages = set([config.STORAGE_TYPE_ISCSI])

    @pytest.fixture(scope='function')
    def initializer_TestCase14944(self, request):
        """
        Create a vm and two direct LUN disks
        """
        request.addfinalizer(self.finalizer_BaseTestCase)
        self.permutations = (
            filter(
                lambda w: w[0] != w[1],
                itertools.permutations(TEST_INTERFACES, 2)
            )
        )
        self.create_vm_setup()
        self.disk_aliases = []
        for idx in range(len(TEST_INTERFACES)):
            disk_args = config.disk_args.copy()
            disk_args['interface'] = TEST_INTERFACES[idx]
            disk_args['alias'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
            disk_args['type_'] = config.STORAGE_TYPE_ISCSI
            disk_args["lun_address"] = config.UNUSED_LUN_ADDRESSES[idx]
            disk_args["lun_target"] = config.UNUSED_LUN_TARGETS[idx]
            disk_args["lun_id"] = config.UNUSED_LUNS[idx]
            if not ll_disks.addDisk(True, **disk_args):
                raise exceptions.DiskException(
                    "Unable to create disk %s" % disk_args['alias']
                )
            self.disk_aliases.append(disk_args['alias'])

        for disk in self.disk_aliases:
            if not ll_disks.attachDisk(True, disk, self.vm_name, active=True):
                raise exceptions.DiskException(
                    "Unable to attach disk %s to vm %s"
                    % (disk_args['alias'], self.vm_name)
                )

    @polarion("RHEVM-14944")
    @pytest.mark.usefixtures("initializer_TestCase14944")
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


class BaseOneDiskAttachedTestCase(BaseTestCase):

    base_interface = config.INTERFACE_VIRTIO
    new_interface = config.INTERFACE_VIRTIO_SCSI

    @pytest.fixture(scope='function')
    def initialize_BaseOneDiskAttachedTestCase_fixture(self, request):
        """
        Initializer and finalizer call for BaseOneDiskAttachedTestCase
        """
        request.addfinalizer(self.finalizer_BaseTestCase)
        self.initialize_BaseOneDiskAttachedTestCase()

    def initialize_BaseOneDiskAttachedTestCase(self):
        """
        Create a vm with a disk attached
        """
        self.create_vm_setup()
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        disk_args = config.disk_args.copy()
        disk_args['interface'] = self.base_interface
        disk_args['wait'] = False
        disk_args['alias'] = self.disk_alias
        disk_args['storagedomain'] = self.storage_domain
        if not ll_vms.addDisk(True, self.vm_name, **disk_args):
            raise exceptions.DiskException(
                "Unable to create disk %s" % disk_args['alias']
            )
        if not ll_disks.wait_for_disks_status(self.disk_alias):
            raise exceptions.DiskException(
                "Failed to wait for disk %s status OK" % self.disk_alias
            )
        self.disk_id = ll_disks.get_disk_obj(self.disk_alias).get_id()

    def update_disk_interface(self, positive=True, check_guest=True):
        """
        Update the disk interface to new_interface and assert the result
        according to postivie
        """
        status = ll_disks.updateDisk(
            positive, vmName=self.vm_name, alias=self.disk_alias,
            interface=self.new_interface
        )
        assert status, "Changing disk %s interface from %s to %s %s " % (
            self.disk_alias, self.base_interface, self.new_interface,
            'failed' if positive else 'passed'
        )
        logger.info(
            "Disk %s changed interface from %s to %s %s",
            self.disk_alias, self.base_interface, self.new_interface,
            'passed' if positive else 'failed'
        )
        if positive:
            expected_interface = self.new_interface
        else:
            expected_interface = self.base_interface

        self.check_engine_disk_interface(expected_interface)

        if positive and check_guest:
            self.check_guest_os_disk_interface(expected_interface)


@attr(tier=2)
class TestCase14945(BaseTestCase):
    """
    RHEVM-14945 - Shared disk attached to serveral VMs with different
    interface types

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-6245
    """
    __test__ = True

    @pytest.fixture(scope='function')
    def initializer_TestCase14945(self, request):
        """
        Create vms and shared disk
        """
        def finalizer_TestCase14945():
            if not ll_vms.safely_remove_vms(self.vm_names):
                BaseTestCase.test_failed = True
                logger.error("Failed to remove vms %s", self.vm_names)
            if not ll_disks.deleteDisk(True, self.disk_alias):
                BaseTestCase.test_failed = False
                logger.error("Failed to remove disk %s", self.disk_alias)
            BaseTestCase.teardown_exception()
        request.addfinalizer(finalizer_TestCase14945)

        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.vm_names = []
        for idx in range(2):
            vm_args_copy = config.create_vm_args.copy()
            vm_args_copy['vmName'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_VM
            )
            vm_args_copy['storageDomainName'] = self.storage_domain
            if not storage_helpers.create_vm_or_clone(**vm_args_copy):
                raise exceptions.VMException(
                    "Unable to create vm %s" % self.vm_name
                )
            self.vm_names.append(vm_args_copy['vmName'])
        disk_args = config.disk_args.copy()
        disk_args['interface'] = config.INTERFACE_IDE
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        disk_args['shareable'] = True
        disk_args['format'] = config.RAW_DISK
        disk_args['sparse'] = False
        disk_args['storagedomain'] = self.storage_domain
        disk_args['alias'] = self.disk_alias
        if not ll_disks.addDisk(True, **disk_args):
            raise exceptions.DiskException(
                "Unable to create disk %s" % disk_args['alias']
            )
        if not ll_disks.wait_for_disks_status([self.disk_alias]):
            raise exceptions.DiskException(
                "Failed to wait for disk %s status OK" % self.disk_alias
            )

        self.disk_id = ll_disks.get_disk_obj(self.disk_alias).get_id()

    @pytest.mark.usefixtures("initializer_TestCase14945")
    @polarion("RHEVM-14945")
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
        assert ll_disks.attachDisk(
            positive=True, alias=self.disk_alias, vm_name=self.vm_names[0],
            active=False, disk_id=self.disk_id,
            interface=config.INTERFACE_IDE
        )
        assert ll_vms.activateVmDisk(
            True, self.vm_names[0], diskId=self.disk_id
        )
        assert ll_disks.attachDisk(
            positive=True, alias=self.disk_alias, vm_name=self.vm_names[1],
            active=False, disk_id=self.disk_id,
            interface=config.INTERFACE_VIRTIO
        )
        assert ll_vms.activateVmDisk(
            True, self.vm_names[1], diskId=self.disk_id
        )
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
        ll_vms.stop_vms_safely(self.vm_names)
        assert ll_disks.updateDisk(
            True, vmName=self.vm_names[0], alias=self.disk_alias,
            interface=config.INTERFACE_VIRTIO
        )
        assert ll_disks.updateDisk(
            True, vmName=self.vm_names[1], alias=self.disk_alias,
            interface=config.INTERFACE_IDE
        )
        ll_vms.start_vms(self.vm_names, wait_for_ip=True)
        self.check_engine_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[0]
        )
        self.check_engine_disk_interface(
            config.INTERFACE_IDE, self.vm_names[1]
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_VIRTIO, self.vm_names[0]
        )
        self.check_guest_os_disk_interface(
            config.INTERFACE_IDE, self.vm_names[1]
        )


@attr(tier=2)
class TestCase14946(BaseTestCase):
    """
    RHEVM-14946 - Change disks to IDE for a large number of PCI devices

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14946
    """
    __test__ = True

    @pytest.fixture(scope='function')
    def initializer_TestCase14946(self, request):
        """
        Create a vm and 10 Virtio disks and attach them to the vm
        """
        request.addfinalizer(self.finalizer_BaseTestCase)
        self.create_vm_setup()
        self.disk_aliases = []
        for disk in range(10):
            disk_args = config.disk_args.copy()
            disk_args['interface'] = config.INTERFACE_VIRTIO
            disk_args['alias'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
            disk_args['wait'] = False
            disk_args['storagedomain'] = self.storage_domain
            if not ll_vms.addDisk(True, self.vm_name, **disk_args):
                raise exceptions.DiskException(
                    "Unable to create disk %s" % disk_args['alias']
                )
            self.disk_aliases.append(disk_args['alias'])
        if not ll_disks.wait_for_disks_status(self.disk_aliases):
            raise exceptions.DiskException(
                "Failed to wait for disk %s status OK" % self.disk_aliases
            )

    @polarion("RHEVM-14946")
    @pytest.mark.usefixtures("initializer_TestCase14946")
    def test_change_disk_ide_large_number_devices(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create and attach 10 disks to the VM with VirtIO interface

        Test flow:
        - While the VM is stopped, change all the disks interface to IDE ->
        Should fail, It shouldn't be allowed to have more than 3 IDE disks
        attached to the VM
        """
        for disk in self.disk_aliases[:3]:
            assert ll_disks.updateDisk(
                True, vmName=self.vm_name, alias=disk,
                interface=config.INTERFACE_IDE
            ), "Error changing disk interface to IDE"
        assert ll_disks.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_aliases[3],
            interface=config.INTERFACE_IDE
        ), (
            "It shouldn't be possible to have more than 3 disks with "
            "interface IDE attached to a VM"
        )


@attr(tier=2)
class TestCase14947(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14947 - Negative - Try to change disk interface attach to a running
    VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14947
    """
    __test__ = True

    @polarion("RHEVM-14947")
    @pytest.mark.usefixtures("initialize_BaseOneDiskAttachedTestCase_fixture")
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
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        self.update_disk_interface(positive=False)


@attr(tier=2)
class TestCase14948(BaseTestCase):
    """
    RHEVM_14948 - Negative - Try to attach disk to a VM without the interface
    parameter set

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14948
    """
    __test__ = True

    @pytest.fixture(scope='function')
    def initializer_TestCase14948(self, request):
        """
        Create the vm and the shared disk
        """
        def finalizer_TestCase1948():
            """
            Remove the created shared disk
            """
            if not ll_disks.deleteDisk(True, self.disk_alias):
                logger.error("Failed to remove disk %s", self.disk_alias)
                BaseTestCase.test_failed = False
            self.finalizer_BaseTestCase()

        request.addfinalizer(finalizer_TestCase1948)
        self.create_vm_setup()
        disk_args = config.disk_args.copy()
        disk_args['interface'] = config.INTERFACE_IDE
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        disk_args['shareable'] = True
        disk_args['format'] = config.RAW_DISK
        disk_args['sparse'] = False
        disk_args['storagedomain'] = self.storage_domain
        disk_args['alias'] = self.disk_alias
        if not ll_disks.addDisk(True, **disk_args):
            raise exceptions.DiskException(
                "Unable to create disk %s" % disk_args['alias']
            )
        if not ll_disks.wait_for_disks_status([self.disk_alias]):
            raise exceptions.DiskException(
                "Failed to wait for disk %s status OK" % self.disk_alias
            )

    @polarion("RHEVM-14948")
    @pytest.mark.usefixtures("initializer_TestCase14948")
    def test_attach_disk_without_interface(self):
        """
        Test setup:
        - Create a VM with disk attached and install OS
        - Create a shared disk

        Test flow:
        - Attach the shared disk to the VM and don't specify the interface
        type -> Should fail
        """
        disk_obj = ll_disks.get_disk_obj(self.disk_alias)
        assert ll_disks.attachDisk(
            positive=True, alias=disk_obj.get_alias(),
            vm_name=self.vm_name, active=False, disk_id=disk_obj.get_id(),
            interface=None
        ), (
            "Succeeded to attach a disk to a vm without specifying "
            "the disk interface"
        )


@attr(tier=2)
class TestCase14949(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14949 - Disk interface after restore snapshot

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14949
    """
    __test__ = True

    @polarion("RHEVM-14949")
    @pytest.mark.usefixtures("initialize_BaseOneDiskAttachedTestCase_fixture")
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
        ll_vms.addSnapshot(True, self.vm_name, self.snapshot_name)
        self.update_disk_interface()
        ll_vms.restore_snapshot(True, self.vm_name, self.snapshot_name)
        self.check_engine_disk_interface(self.base_interface)
        self.check_guest_os_disk_interface(self.base_interface)


@attr(tier=2)
class TestCase14955(BaseOneDiskAttachedTestCase):
    """
    RHEVM_14955 - Change disk interface for a suspended VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM-14955
    """
    __test__ = True

    @polarion("RHEVM-14955")
    @pytest.mark.usefixtures("initialize_BaseOneDiskAttachedTestCase_fixture")
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
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.suspendVm(True, self.vm_name)
        self.update_disk_interface(positive=False)


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__, update_vm.__name__, add_disk.__name__
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

    @polarion("RHEVM3-16716")
    def test_attach_virtio_scsi_disk_to_unsupported_vm(self):
        """
        Attach a disk to a VM when the interface is virtio-scsi and the VM does
        not support this interface
        """
        if not ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, interface=config.VIRTIO_SCSI
        ):
            raise exceptions.DiskException(
                "Succeeded to attach disk %s to vm %s" %
                (self.disk_name, self.vm_name)
            )
