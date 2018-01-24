"""
Virtio-blk data plane helpers
"""
import logging
import xml.etree.ElementTree as ET

import config as conf
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


def check_iothreads(vm_name, number_of_iothreads):
    """
    1. Check number of IO threads
    2. Check number of SCSI controllers and controllers IO threads
    3. Check VM disks IO threads
    4. Check that each disk was assigned a unique controller, e.g. for each
        disk iothread there is corresponding controller iothread

    Args:
        vm_name (str): VM name
        number_of_iothreads (int): Number of VM IO threads
    """
    number_of_iothreads = str(number_of_iothreads)
    vm_xml = get_vm_xml(vm_name=vm_name)
    parsed_xml = ET.fromstring(vm_xml)
    cntrlrs_drivers = parsed_xml.findall(
        "*/controller[@model='virtio-scsi'][@type='scsi']/driver[@iothread]"
    )

    disks_drivers = parsed_xml.findall(
        "*/disk[@device='disk']/driver[@iothread]"
    )
    assert parsed_xml.find('iothreads').text == number_of_iothreads, \
        "Iothreads number is incorrect"
    assert len(cntrlrs_drivers) == number_of_iothreads,\
        "Iothreads controllers number is incorrect"
    assert len(disks_drivers) == number_of_iothreads,\
        "Iothreads disks number is incorrect"
    cntrlrs_ids = [c.text for c in cntrlrs_drivers]
    disks_ids = [d.text for d in disks_drivers]
    assert sorted(cntrlrs_ids) == sorted(disks_ids)
