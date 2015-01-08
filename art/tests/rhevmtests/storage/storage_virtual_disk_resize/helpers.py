"""
3.3 Feature: Virtual Disk Resize test helpers functions
"""

import logging
from utilities.machine import Machine
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level.disks import waitForDisksState
from art.rhevm_api.tests_lib.low_level.vms import (
    activateVmDisk, waitForVMState, start_vms,
)

from art.rhevm_api.tests_lib.low_level import disks
from art.test_handler import exceptions
import shlex
from art.test_handler.exceptions import CanNotFindIP
from rhevmtests.storage.helpers import get_vm_ip

import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISKS_NAMES = list()
DISK_TIMEOUT = 250
FILTER = '[sv]d'
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'

DD_TIMEOUT = 1500


def prepare_disks_for_vm(vm_name, disks_to_prepare):
    """
    Attach disks to vm
    Parameters:
        * vm_name - name of vm which disk should attach to
        * disks_to_prepare - list of disks aliases
        * read_only - if the disks should attach as RO disks

    Raise DiskException if operation fails
    """
    for disk in disks_to_prepare:
        assert waitForDisksState(disk, timeout=DISK_TIMEOUT)
        logger.info("Attaching disk %s to vm %s",
                    disk, vm_name)
        status = disks.attachDisk(True, disk, vm_name, active=False)
        if not status:
            raise exceptions.DiskException("Failed to attach disk %s to"
                                           " vm %s"
                                           % (disk, vm_name))

        logger.info("Plugging disk %s", disk)
        status = activateVmDisk(True, vm_name, disk)
        if not status:
            raise exceptions.DiskException("Failed to plug disk %s "
                                           "to vm %s"
                                           % (disk, vm_name))


def get_vm_storage_devices(vm_name):
    """
    Function that returns vm storage devices
    Parameters:
        * vm_name - name of vm which write operation should occur on
    Return: list of devices (e.g [vdb,vdc,...]) and boot device,
            or raise EntityNotFound if error occurs
    """
    start_vms([vm_name], max_workers=1, wait_for_ip=False)
    assert waitForVMState(vm_name)
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'

    vm_devices = vm_machine.get_storage_devices(filter=FILTER)
    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")

    vm_devices = [device for device in vm_devices if device != boot_disk]

    return vm_devices, boot_disk


def verify_write_operation_to_disk(vm_name, disk_number=0):
    """
    Function that perform dd command to disk
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * disk_number - disk number from devices list
    Return: ecode and output, or raise EntityNotFound if error occurs
    """
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')
    vm_devices, boot_disk = get_vm_storage_devices(vm_name)

    command = DD_COMMAND % (boot_disk, vm_devices[disk_number])

    ecode, out = vm_machine.runCmd(shlex.split(command), timeout=DD_TIMEOUT)

    return ecode, out


def get_volume_size(hostname, user, password, disk_object, dc_obj):
    """
    Get volume size in GB
    Author: ratamir
    Parameters:
        * hostname - ip or fqdn of the host
        * user - user name for host
        * password - password for host
        * disk_object - disk object that need checksum
        * dc_obj - data center that the disk belongs to
    Return:
        Volume size (integer), or raise exception otherwise
    """
    host_machine = Machine(host=hostname, user=user,
                           password=password).util('linux')

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sp_id = dc_obj.get_id()

    lv_size = host_machine.get_volume_size(sd_id, sp_id, image_id, vol_id)
    logger.info("Volume size of disk %s is %s GB",
                disk_object.get_alias(), lv_size)

    return lv_size


def get_vm_device_size(vm_name, device_name):
    """
    Get vm device size in GB
    Author: ratamir
    Parameters:
        * vm_name - name of vm
        * device_name - name of device

    Return:
        VM device size (integer) output, or raise exception otherwise
    """
    try:
        vm_ip = get_vm_ip(vm_name)
    except CanNotFindIP:
        raise exceptions.VMException("No IP found for vm %s: ", vm_name)

    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')

    device_size = vm_machine.get_storage_device_size(device_name)
    logger.info("Device %s size: %s GB", device_name, device_size)

    return device_size
