"""
3.3 Feature: Virtual Disk Resize test helpers functions
"""

import logging
import re
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import vms as ll_vms

from rhevmtests.storage import helpers as storage_helpers

import config

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 250
GB = 1024 ** 3
MB = 1024 ** 2


# TODO: Move this function to the storage.helpers and remove
# other instances where the code does the same
def get_vm_storage_devices(vm_name):
    """
    Function that returns vm storage devices
    Parameters:
        * vm_name - name of vm which write operation should occur on
    Return: list of devices (e.g [vdb,vdc,...]) and boot device,
            or raise EntityNotFound if error occurs
    """
    if ll_vms.get_vm_state(vm_name) != config.VM_UP:
        ll_vms.start_vms([vm_name], max_workers=1, wait_for_ip=True)
        assert ll_vms.waitForVMState(vm_name)
    output = storage_helpers.get_vm_boot_disk(vm_name)
    boot_disk = re.search(storage_helpers.REGEX_DEVICE_NAME, output).group()

    vm_devices = storage_helpers.get_storage_devices(vm_name)

    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")

    vm_devices = [device for device in vm_devices if device != boot_disk]

    return vm_devices, boot_disk


def get_volume_size(
    hostname, disk_object, dc_obj, size_format='g'
):
    """
    Get volume size in GB

    Author: ratamir

    Args:
        hostname (str): Name of the host to use
        disk_object (Disk object): Disk object that need checksum
        dc_obj (DataCenter object): Data center that the disk belongs to
        size_format (str): 'b': bytes, 'm': Mb, 'g': Gb

    Returns:
        int: Volume size, or -1 in case of an error
    """
    volume_info = storage_helpers.get_volume_info(
        hostname, disk_object, dc_obj
    )
    if volume_info:
        if size_format is 'b':
            return int(volume_info['truesize'])
        if size_format is 'm':
            return int(volume_info['truesize']) / MB
        return int(volume_info['truesize']) / GB
    logger.error("Could not calculate the volume size")
    return -1


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
    device_size = storage_helpers.get_storage_device_size(vm_name, device_name)
    logger.info("Device %s size: %s GB", device_name, device_size)

    return device_size
