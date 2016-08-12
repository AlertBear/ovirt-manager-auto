"""
3.5 Get Device Name
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Get_Device_Name
"""
import config
import logging
import shlex

from art.rhevm_api.tests_lib.low_level import disks, jobs, storagedomains, vms
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import attr, StorageTest as BaseTestCase
from rhevmtests.storage import helpers
from utilities.machine import LINUX, Machine
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

SHARED_DISK = "sharable_disk_%s"
NON_SHARED_DISK = "non_sharable_disk_%s"

ALIAS = "alias"

POLARION_PROJECT = "RHEVM3-"

# Global list to hold VMs with VirtIO-SCSI Enabled set to False
VMS_WITH_VIRTIO_SCSI_FALSE = list()

STORAGE_DEVICES_FILTER = '[sv]d[a-z]'

# Parameters for disk (alias and storage domain are filled in per test case)
disk_kwargs = {
    "interface": config.DISK_INTERFACE_VIRTIO,
    "alias": '',
    "format": config.DISK_FORMAT_RAW,
    "provisioned_size": config.DISK_SIZE,
    "bootable": False,
    "storagedomain": '',
    "shareable": False,
    "sparse": False,
}


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardown for the permutation of disks
    used as part of the tests
    """
    __test__ = False
    vm_name = None
    storage_domain = None
    create_disk_permutations = False
    polarion_test_case = None

    def setUp(self):
        """
        General setup function that picks a storage domain to use (matching
        the current storage type), initializes the disk aliases and
        descriptions list and the disk aliases list, then picks the first
        2 GE VMs from the configuration file
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        self.disk_aliases = list()
        vm_names = storage_helpers.get_vms_for_storage(self.storage)
        self.vm_name = vm_names[0]
        self.vm_name_2 = vm_names[1]

        # Create disk permutations for the relevant cases
        if self.create_disk_permutations:
            self.create_disks_using_permutations()

    def create_disks_using_permutations(self):
        """
        Creates a set of disks to be used with all the Get Device name
        tests, and saves a list with the aliases of the created disks
        """
        self.disk_aliases = (
            helpers.create_disks_from_requested_permutations(
                self.storage_domain, (config.VIRTIO, config.VIRTIO_SCSI),
                config.DISK_SIZE, test_name=self.polarion_test_case
            )
        )

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
        disk_args = disk_kwargs.copy()
        disk_args['storagedomain'] = self.storage_domain
        # Message used as part of the various log messages (shared or
        # non-shared disk, setting default to 'non-shared'
        disk_message = "shared" if is_disk_shared else "non-shared"
        disk_args[ALIAS] = NON_SHARED_DISK % self.polarion_test_case
        if is_disk_shared:
            disk_args[ALIAS] = SHARED_DISK % self.polarion_test_case
            disk_args['shareable'] = True

        logger.info("Creating %s disk '%s'", disk_message, disk_args[ALIAS])
        if not disks.addDisk(True, **disk_args):
            raise exceptions.DiskException("Failed to create %s disk %s"
                                           % (disk_message,
                                              disk_args[ALIAS]))
        disks.wait_for_disks_status([disk_args[ALIAS]])
        self.disk_aliases.append(disk_args[ALIAS])

        for vm_name in vm_names:
            logger.info("Attaching %s disk '%s' to VM '%s'", disk_message,
                        disk_args[ALIAS], vm_name)
            if not disks.attachDisk(True, disk_args[ALIAS], vm_name):
                raise exceptions.DiskException("Failed to attach %s disk '%s' "
                                               "to vm %s" %
                                               (disk_message,
                                                disk_args[ALIAS], vm_name))

    def attach_disk_permutations_and_verify_in_os(self, hot_plug=False,
                                                  hot_unplug=False):
        """
        Attaches all disks (created using permutations) to the first VM
        used, and verified each disk is visible on the OS using vd* or sd*
        depending on its interface.
        Note that this function allows for cold plug, hot plug and hot
        unplug (which is used in conjunction with hot plug)

        Used by Polarion cases 4572, 4575 and 4576
        """
        assert vms.startVm(True, self.vm_name, config.VM_UP, True)

        self.current_storage_devices = helpers.get_storage_devices(
            self.vm_name, STORAGE_DEVICES_FILTER
        )
        if not hot_plug:
            vms.stop_vms_safely([self.vm_name])

        for disk_alias in self.disk_aliases:
            logger.info("Attaching disk '%s' to VM '%s'", disk_alias,
                        self.vm_name)
            assert disks.attachDisk(True, disk_alias, self.vm_name)
            assert disks.wait_for_disks_status(disk_alias)

            if not hot_plug:
                assert vms.startVm(True, self.vm_name, config.VM_UP, True)

            # TODO: This is a workaround for bug
            # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
            vm_ip = helpers.get_vm_ip(self.vm_name)
            vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                                 password=config.VM_PASSWORD).util(LINUX)
            vm_machine.runCmd(shlex.split("udevadm trigger"))

            disk_logical_volume_name = vms.get_vm_disk_logical_name(
                self.vm_name, disk_alias, parse_logical_name=True
            )
            self.current_storage_devices = (
                helpers.get_storage_devices(
                    self.vm_name, STORAGE_DEVICES_FILTER
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
                assert disks.detachDisk(True, disk_alias, self.vm_name)
                self.current_storage_devices = (
                    helpers.get_storage_devices(
                        self.vm_name, STORAGE_DEVICES_FILTER
                    )
                )
                assert disk_logical_volume_name not in (
                    self.current_storage_devices
                ), (
                    "The disk created '%s' was found after being attached to "
                    "the VM" % disk_alias
                )

            if not hot_plug:
                vms.stop_vms_safely([self.vm_name])

    def create_and_attach_disk_to_vms_performing_os_validation(
        self, is_disk_shared, vm_names
    ):
        """
        Function creates a shared or non-shared disk and attaches it to a list
        of VMs
        """
        self.current_storage_devices = dict()
        self.create_and_attach_disk_to_vms(is_disk_shared, vm_names)

        vms.start_vms(
            vm_names, wait_for_status=config.VM_UP)

        for vm_name in vm_names:
            # TODO: This is a workaround for bug
            # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
            vm_ip = helpers.get_vm_ip(vm_name)
            vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                                 password=config.VM_PASSWORD).util(LINUX)
            vm_machine.runCmd(shlex.split("udevadm trigger"))

            self.current_storage_devices[vm_name] = (
                helpers.get_storage_devices(
                    vm_name, STORAGE_DEVICES_FILTER
                )
            )

            if is_disk_shared:
                disk_logical_volume_name = vms.get_vm_disk_logical_name(
                    vm_name, SHARED_DISK % self.polarion_test_case,
                    parse_logical_name=True
                )
            else:
                disk_logical_volume_name = vms.get_vm_disk_logical_name(
                    vm_name, NON_SHARED_DISK % self.polarion_test_case,
                    parse_logical_name=True
                )
            self.verify_logical_device_naming(config.VIRTIO,
                                              disk_logical_volume_name)
            assert disk_logical_volume_name in (
                self.current_storage_devices[vm_name]
            ), (
                "The disk volume name '%s' was not found after being attached "
                "to the VM" % disk_logical_volume_name
            )

        vms.stop_vms_safely(vm_names)

    def tearDown(self):
        """
        Power off the VMs and remove all disks created for the tests
        """
        vms.stop_vms_safely([self.vm_name, self.vm_name_2])
        for disk_alias in self.disk_aliases:
            if not disks.deleteDisk(True, disk_alias):
                self.test_failed = True
                logger.error("Deleting disk '%s' failed", disk_alias)
        jobs.wait_for_jobs([config.ENUMS['job_remove_disk']])
        self.teardown_exception()


@attr(tier=2)
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
    create_disk_permutations = True

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4572"""
        self.attach_disk_permutations_and_verify_in_os()


@attr(tier=2)
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

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_one_shared_disk_on_2_vms(self):
        """ Polarion case 4573"""
        self.create_and_attach_disk_to_vms_performing_os_validation(
            True, [self.vm_name, self.vm_name_2]
        )


@attr(tier=2)
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

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_one_non_shared_one_shared_disk_on_2_vms(self):
        """ Polarion case 4574"""
        self.create_and_attach_disk_to_vms_performing_os_validation(
            False, [self.vm_name]
        )
        self.create_and_attach_disk_to_vms_performing_os_validation(
            True, [self.vm_name, self.vm_name_2]
        )


@attr(tier=2)
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
    create_disk_permutations = True

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4575"""
        self.attach_disk_permutations_and_verify_in_os(hot_plug=True)


@attr(tier=2)
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
    create_disk_permutations = True

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_basic_flow_get_device_name(self):
        """ Polarion case 4576"""
        self.attach_disk_permutations_and_verify_in_os(
            hot_plug=True, hot_unplug=True
        )
