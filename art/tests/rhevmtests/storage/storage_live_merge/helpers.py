"""
Live merge test helpers functions
"""
import config
import logging
import shlex

from art.rhevm_api.tests_lib.low_level import disks, vms
from art.test_handler import exceptions
from rhevmtests.storage import helpers
from utilities.machine import LINUX, Machine

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
CREATION_DISKS_TIMEOUT = 600
DISK_NAMES = dict()
MOUNT_POINTS = dict()


def prepare_disks_with_fs_for_vm(storage_domain, storage_type, vm_name):
    """
    Prepare disks with filesystem for vm

    :param storage_domain: Name of the storage domain to be used for
    disk creation
    :type storage_domain: str
    :param storage_type: Storage type to be used with the disk creation
    :type storage_type: str
    :param vm_name: Name of the VM under which a disk with a file system
    will be created
    :type vm_name: str
    """
    global DISK_NAMES
    DISK_NAMES[storage_type] = list()
    MOUNT_POINTS[storage_type] = list()
    vm_ip = helpers.get_vm_ip(vm_name)
    vm_machine = Machine(
        host=vm_ip, user=config.VM_USER, password=config.VM_PASSWORD
    ).util(LINUX)
    logger.info('Creating disks for test')
    disk_names = helpers.start_creating_disks_for_test(
        sd_name=storage_domain, sd_type=storage_type
    )
    DISK_NAMES[storage_type] = disk_names

    if not disks.wait_for_disks_status(
        DISK_NAMES[storage_type], timeout=CREATION_DISKS_TIMEOUT
    ):
        raise exceptions.DiskException("Some disks are still locked")
    helpers.prepare_disks_for_vm(vm_name, DISK_NAMES[storage_type])

    # TODO: Workaround for bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
    vm_machine.runCmd(shlex.split("udevadm trigger"))

    for disk_alias in DISK_NAMES[storage_type]:
        disk_logical_volume_name = vms.get_vm_disk_logical_name(
            vm_name, disk_alias
        )
        if not disk_logical_volume_name:
            # This function is used to test whether logical volume was
            # found, raises an exception if it wasn't found
            raise exceptions.DiskException(
                "Failed to get %s disk logical name" % disk_alias
            )

        logger.info(
            "The logical volume name for the requested disk is: '%s'",
            disk_logical_volume_name
        )
        device_name = disk_logical_volume_name.split('/')[-1]
        dev_size = vm_machine.get_storage_device_size(device_name)
        # Create a partition of the size of the disk, taking into account
        # the usual offset for logical partitions, setting to 10 MB
        partition = vm_machine.createPartition(
            disk_logical_volume_name, dev_size * config.GB - config.MB * 10,
        )
        assert partition
        mount_point = vm_machine.createFileSystem(
            disk_logical_volume_name, partition, helpers.FILESYSTEM,
            ('/' + device_name),
        )
        MOUNT_POINTS[storage_type].append(mount_point)
    logger.info(
        "Mount points for new disks: %s", MOUNT_POINTS[storage_type]
    )
