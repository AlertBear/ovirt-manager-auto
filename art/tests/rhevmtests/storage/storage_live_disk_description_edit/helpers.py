"""
3.5 Feature: Helper module for Live disk description edit
"""
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
import logging

logger = logging.getLogger(__name__)


def verify_vm_disk_description(vm_name, disk_alias, expected_disk_description):
    """
    Retrieves the requested VM's disk description

    __author__ = "glazarov"
    :param vm_name: name of the VM from which the disk description will be
    retrieved
    :type vm_name: str
    :param disk_alias: alias of the disk from which the disk description
    will be retrieved
    :type disk_alias: str
    :param expected_disk_description: the expected disk description
    :type expected_disk_description: str
    :returns: True when the expected disk description matches the actual disk
    description, False otherwise
    :rtype: bool
    """
    logger.info("Retrieving the disk description from VM '%s'", vm_name)
    disk_object = ll_disks.getVmDisk(vm_name, disk_alias)
    logger.info(
        "Expected description: %s, actual description: %s",
        expected_disk_description, disk_object.get_description()
    )
    return disk_object.get_description() == expected_disk_description
