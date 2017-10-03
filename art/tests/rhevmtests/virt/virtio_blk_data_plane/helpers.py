"""
Virtio-blk data plane helpers
"""
import logging
import re

import config as conf
from art.unittest_lib import testflow
from rhevmtests import helpers

logger = logging.getLogger(__name__)


def get_vm_xml(vm_name):
    """
    Get VM dump XML from the host

    Args:
        vm_name (str): VM name

    Returns:
        str: VM dump XML
    """
    host_resource = helpers.get_host_resource_of_running_vm(vm=vm_name)
    virsh_cmd = conf.VIRSH_VM_DUMP_XML_CMD.split()
    virsh_cmd.append(vm_name)
    rc, out, _ = host_resource.run_command(command=virsh_cmd)
    if rc:
        return ""
    logger.debug("VM %s dump XML: %s", vm_name, out)
    return out


def get_number_of_iothreads(vm_xml):
    """
    Get number of IO threads from VM dump XML

    Args:
        vm_xml (str): VM dump XML

    Returns:
        int: Number of IO threads
    """
    iothreads = re.search(pattern=conf.IOTHREADS_REGEXP, string=vm_xml)
    if not iothreads:
        return 0
    return int(iothreads.group(1))


def get_iothreads_controllers(vm_xml):
    """
    Get SCSI controllers from VM dump XML

    Args:
        vm_xml (str): VM dump XML

    Returns:
        list: list with SCSI controllers indexes
    """
    return re.findall(
        pattern=conf.IOTHREADS_CONTROLLERS_REGEXP,
        string=vm_xml,
        flags=re.DOTALL
    )


def check_iothreads_number(vm_xml, expected_number_of_iothreads):
    """
    Verify that VM has number of IO threads equal to expected value

    Args:
        vm_xml (str): VM dump XML
        expected_number_of_iothreads (int): Expected number of IO threads

    Returns:
        bool: True, if VM has number of IO threads equal to expected value,
            otherwise False
    """
    testflow.step(
        "Verify that the number of IO threads equal to %s",
        expected_number_of_iothreads
    )
    return get_number_of_iothreads(
        vm_xml=vm_xml
    ) == expected_number_of_iothreads


def check_controllers_number(vm_xml, expected_number_of_controllers):
    """
    Verify that number of VM SCSI controllers equal to the expected value

    Args:
        vm_xml (str): VM dump XML
        expected_number_of_controllers (int): Expected number of controllers

    Returns:
        bool: True, if VM number of controllers equal to the expected value and
            each controller has separate IO thread, otherwise False
    """
    controllers = get_iothreads_controllers(vm_xml=vm_xml)
    testflow.step(
        "Verify that the number of SCSI controllers equal to %s",
        expected_number_of_controllers
    )
    return len(controllers) == expected_number_of_controllers


def check_vm_disks_iothreads(vm_xml, number_of_iothreads):
    """
    Verify that each VM disk has correct IO thread

    Args:
        vm_xml (str): VM dump XML
        number_of_iothreads (int): Number of VM IO threads

    Returns:
        bool: True, if each VM disk has correct IO thread, otherwise False
            (in the case when number of IO threads bigger than number of VM
            disks, each VM disk must have separate IO thread)
    """
    for pattern in (conf.VIRTIO_DISKS_REGEXP, conf.VIRTIO_SCSI_DISKS_REGEXP):
        disks = re.findall(pattern=pattern, string=vm_xml, flags=re.DOTALL)
        if disks:
            iothreads = [
                x for n, x in enumerate(disks)
                if x not in disks[:n]
            ]
            number_of_disks_iothreads = len(iothreads)
            number_of_disks = len(disks)
            if number_of_disks >= number_of_iothreads:
                if number_of_iothreads != number_of_disks_iothreads:
                    return False
            elif number_of_disks != number_of_disks_iothreads:
                return False
        return True


def check_iothreads(vm_name, number_of_iothreads):
    """
    1. Check number of IO threads
    2. Check number of SCSI controllers and controllers IO threads
    3. Check VM disks IO threads

    Args:
        vm_name (str): VM name
        number_of_iothreads (int): Number of VM IO threads
    """
    vm_xml = get_vm_xml(vm_name=vm_name)
    assert check_iothreads_number(
        vm_xml=vm_xml, expected_number_of_iothreads=number_of_iothreads
    )
    assert check_controllers_number(
        vm_xml=vm_xml, expected_number_of_controllers=number_of_iothreads
    )
    assert check_vm_disks_iothreads(
        vm_xml=vm_xml, number_of_iothreads=number_of_iothreads
    )
