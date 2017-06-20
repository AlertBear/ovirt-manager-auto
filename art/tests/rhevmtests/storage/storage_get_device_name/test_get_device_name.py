"""
3.5 Get Device Name
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Get_Device_Name
"""
import config
import logging
import pytest
import shlex

from art.rhevm_api.tests_lib.low_level import disks, vms
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from rhevmtests.storage import helpers
from utilities.machine import LINUX, Machine
from rhevmtests.storage.fixtures import (
    delete_disks, initialize_storage_domains,
)
from rhevmtests.storage.storage_get_device_name.fixtures import (
    add_disks_permutation, create_vms_for_test,
)

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

SHARED_DISK = "%s_sharable_disk_%s"
NON_SHARED_DISK = "%s_non_sharable_disk_%s"

# Global list to hold VMs with VirtIO-SCSI Enabled set to False
VMS_WITH_VIRTIO_SCSI_FALSE = list()


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_vms_for_test.__name__,
    delete_disks.__name__,
)
class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardown for the permutation of disks
    used as part of the tests
    """
    __test__ = False
    polarion_test_case = None

    def verify_logical_device_naming(self, disk_interface,
                                     disk_logical_volume_name):
        """
        Disks that are created using interface VirtIO-SCSI should show up as
        sd* in the guest OS, all other disks should show up as vd*
        """
        if disk_interface == config.VIRTIO_SCSI:
            assert disk_logical_volume_name.find("sd") != -1, (
                "The VirtIO-SCSI disk name was not found to use "
                "sd*, the disk logical name is: '%s'" %
                disk_logical_volume_name
            )
        else:
            assert disk_logical_volume_name.find("vd") != -1, (
                "The VirtIO disk name was not found to use "
                "vd*, the disk logical name is: '%s'" %
                disk_logical_volume_name
            )

    def create_and_attach_disk_to_vms(self, is_disk_shared, vm_names):
        """
        Creates a disk (shared or non-shared depending on parameter
        is_disk_shared) and attaches it to the vms passed in (using
        parameter vm_names)
        """
        disk_args = config.disk_args.copy()
        disk_args['format'] = config.RAW_DISK
        disk_args['sparse'] = False
        disk_args['storagedomain'] = self.storage_domain
        # Message used as part of the various log messages (shared or
        # non-shared disk, setting default to 'non-shared'
        disk_message = "shared" if is_disk_shared else "non-shared"
        self.disk_alias = helpers.create_unique_object_name(
            disk_message + self.storage + self.polarion_test_case,
            config.OBJECT_TYPE_DISK
        )
        disk_args['alias'] = self.disk_alias
        if is_disk_shared:
            disk_args['shareable'] = True

        testflow.step("Creating %s disk '%s'", disk_message, self.disk_alias)
        assert disks.addDisk(True, **disk_args), (
            "Failed to create %s disk %s" % (disk_message, self.disk_alias)
        )
        disks.wait_for_disks_status([self.disk_alias])
        self.disks_to_remove.append(self.disk_alias)

        for vm_name in vm_names:
            logger.info(
                "Attaching %s disk '%s' to VM '%s'",
                disk_message, self.disk_alias, vm_name
            )
            assert disks.attachDisk(True, self.disk_alias, vm_name), (
                "Failed to attach %s disk '%s' to vm %s" % (
                    disk_message, self.disk_alias, vm_name
                )
            )

    def attach_disk_permutations_and_verify_in_os(
        self, hot_plug=False, hot_unplug=False
    ):
        """
        Attaches all disks (created using permutations) to the first VM
        used, and verified each disk is visible on the OS using vd* or sd*
        depending on its interface.
        Note that this function allows for cold plug, hot plug and hot
        unplug (which is used in conjunction with hot plug)

        Used by Polarion cases 4572, 4575 and 4576
        """
        testflow.step("Starting VM %s", self.vm_names[0])
        assert vms.startVm(True, self.vm_names[0], config.VM_UP, True)

        self.current_storage_devices = helpers.get_storage_devices(
            self.vm_names[0], helpers.REGEX_DEVICE_NAME
        )
        if not hot_plug:
            vms.stop_vms_safely([self.vm_names[0]])

        for disk_alias in self.disks_to_remove:
            testflow.step(
                "Attaching disk '%s' to VM '%s'", disk_alias, self.vm_names[0]
            )
            assert disks.attachDisk(True, disk_alias, self.vm_names[0])
            assert disks.wait_for_disks_status(disk_alias)

            if not hot_plug:
                assert vms.startVm(True, self.vm_names[0], config.VM_UP, True)

            # TODO: This is a workaround for bug
            # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
            vm_ip = helpers.get_vm_ip(self.vm_names[0])
            vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                                 password=config.VM_PASSWORD).util(LINUX)
            vm_machine.runCmd(shlex.split("udevadm trigger"))

            disk_logical_volume_name = vms.get_vm_disk_logical_name(
                self.vm_names[0], disk_alias, parse_logical_name=True
            )
            self.current_storage_devices = (
                helpers.get_storage_devices(
                    self.vm_names[0], helpers.REGEX_DEVICE_NAME
                )
            )
            assert disk_logical_volume_name in self.current_storage_devices, (
                "The disk created '%s' was found after being "
                "attached to the VM" % disk_alias
            )

            # Retrieve the disk object, and then retrieve its interface
            # needed in verifying the logical device name
            disk_obj = disks.get_disk_obj(disk_alias)
            self.verify_logical_device_naming(disk_obj.get_interface(),
                                              disk_logical_volume_name)

            if hot_unplug:
                assert disks.detachDisk(True, disk_alias, self.vm_names[0])
                self.current_storage_devices = (
                    helpers.get_storage_devices(
                        self.vm_names[0], helpers.REGEX_DEVICE_NAME
                    )
                )
                assert disk_logical_volume_name not in (
                    self.current_storage_devices
                ), (
                    "The disk created '%s' was found after being attached to "
                    "the VM" % disk_alias
                )

            if not hot_plug:
                vms.stop_vms_safely([self.vm_names[0]])

    def create_and_attach_disk_to_vms_performing_os_validation(
        self, is_disk_shared, vm_names
    ):
        """
        Function creates a shared or non-shared disk and attaches it to a list
        of VMs
        """
        self.current_storage_devices = dict()
        self.create_and_attach_disk_to_vms(is_disk_shared, vm_names)
        testflow.step("Starting VMs %s", vm_names)
        vms.start_vms(vm_names, wait_for_status=config.VM_UP)

        for vm_name in vm_names:
            # TODO: This is a workaround for bug
            # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
            vm_ip = helpers.get_vm_ip(vm_name)
            vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                                 password=config.VM_PASSWORD).util(LINUX)
            vm_machine.runCmd(shlex.split("udevadm trigger"))

            self.current_storage_devices[vm_name] = (
                helpers.get_storage_devices(
                    vm_name, helpers.REGEX_DEVICE_NAME
                )
            )

            if is_disk_shared:
                disk_logical_volume_name = vms.get_vm_disk_logical_name(
                    vm_name, self.disk_alias, parse_logical_name=True
                )
            else:
                disk_logical_volume_name = vms.get_vm_disk_logical_name(
                    vm_name, self.disk_alias, parse_logical_name=True
                )
            self.verify_logical_device_naming(
                config.VIRTIO, disk_logical_volume_name
            )
            assert disk_logical_volume_name in (
                self.current_storage_devices[vm_name]
            ), (
                "The disk volume name '%s' was not found after being attached "
                "to the VM" % disk_logical_volume_name
            )
        testflow.step("Powering off VMs %s", vm_names)
        vms.stop_vms_safely(vm_names)


@pytest.mark.usefixtures(
    add_disks_permutation.__name__,
)
class TestCase4572(BasicEnvironment):
    """
    Basic flow - get device name

    Create disks using available permutations, ensure VIrtIO_SCSI disks are
    named using "sd*" and all other disks are named as "vd*" under both the
    Guest OS and when using API

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-4572
    """
    __test__ = True
    polarion_test_case = '4572'

    @polarion("RHEVM3-4572")
    @tier2
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4572"""
        self.attach_disk_permutations_and_verify_in_os()


class TestCase4573(BasicEnvironment):
    """
    Device name of shared disk - 1 disk

    Create a single VirtIO shared disk, attaching it to 2 VMs, ensure that
    both VMs see it as "vd*" under the Guest OS and using API

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-4573
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    polarion_test_case = '4573'
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])

    @polarion("RHEVM3-4573")
    @tier3
    def test_one_shared_disk_on_2_vms(self):
        """ Polarion case 4573"""
        self.create_and_attach_disk_to_vms_performing_os_validation(
            True, [self.vm_names[0], self.vm_names[1]]
        )


class TestCase4574(BasicEnvironment):
    """
    Device name of shared disk - several disks

    Create a single VirtIO shared disk, attaching it to 2 VMs. Ensure that
    both VMs see it as "vd*" under the Guest OS and using API

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-4574
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    polarion_test_case = '4574'
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])

    @polarion("RHEVM3-4574")
    @tier2
    def test_one_non_shared_one_shared_disk_on_2_vms(self):
        """ Polarion case 4574"""
        self.create_and_attach_disk_to_vms_performing_os_validation(
            False, [self.vm_names[0]]
        )
        self.create_and_attach_disk_to_vms_performing_os_validation(
            True, [self.vm_names[0], self.vm_names[1]]
        )


@pytest.mark.usefixtures(
    add_disks_permutation.__name__,
)
class TestCase4575(BasicEnvironment):
    """
    Get device name - hotplug

    Create disks using available permutations, then hotplug each disk,
    ensuring that VIrtIO_SCSI disks are named using "sd*" and all other
    disks are named as "vd*" under both the Guest OS and when using API

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-4575
    """
    __test__ = True
    polarion_test_case = '4575'

    @polarion("RHEVM3-4575")
    @tier2
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4575"""
        self.attach_disk_permutations_and_verify_in_os(hot_plug=True)


@pytest.mark.usefixtures(
    add_disks_permutation.__name__,
)
class TestCase4576(BasicEnvironment):
    """
    Get device name - hotunplug

    Create disks using available permutations, then hotplug each disk,
    ensuring that VIrtIO_SCSI disks are named using "sd*" and all other
    disks are named as "vd*" under both the Guest OS and when using API.
    Hot unplug each of the disk permutations one after the next, ensuring
    they disappear from the OS

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-4576
    """
    __test__ = True
    polarion_test_case = '4576'

    @polarion("RHEVM3-4576")
    @tier2
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4576"""
        self.attach_disk_permutations_and_verify_in_os(
            hot_plug=True, hot_unplug=True
        )
