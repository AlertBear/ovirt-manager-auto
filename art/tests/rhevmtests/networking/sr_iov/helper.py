#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by SR_IOV feature
"""

import logging
from xml.etree import ElementTree

import rhevmtests.networking.config as conf

logger = logging.getLogger("SR_IOV_Helper")


def update_host_nics():
    """
    Clear cache and update first Host NICs
    """
    logger.info("Get all NICs from host %s", conf.HOST_0_NAME)
    conf.VDS_0_HOST.cache.clear()
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics


def get_vlan_id_from_vm_xml(vm):
    """
    Get VLAN id of vm interface from running VM

    Args:
        vm (str): VM name

    Returns:
        str: VLAN ID

    Raises:
        NetworkException: If VLAN not found among VM interfaces
    """
    logger.info("Get VLAN ID from %s XML", vm)
    dump_xml_cmd = ["virsh", "-r", "dumpxml", vm]
    rc, xml_output, _ = conf.VDS_0_HOST.run_command(dump_xml_cmd)
    assert not rc

    xml_obj = ElementTree.fromstring(xml_output)
    interfaces = xml_obj.find("devices").findall("interface")
    vlan_interface = filter(
        lambda x: x is not None, [i.find("vlan") for i in interfaces]
    )
    assert vlan_interface, "VLAN not found on VM %s interfaces" % vm
    return vlan_interface[0].find("tag").get("id")
