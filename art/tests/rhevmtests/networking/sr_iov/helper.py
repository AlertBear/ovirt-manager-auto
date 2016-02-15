#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by SR_IOV feature
"""

import logging
import config as conf
from xml.etree import ElementTree
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest

logger = logging.getLogger("SR_IOV_Helper")


def update_host_nics():
    """
    Clear cache and update first Host NICs
    """
    logger.info("Get all NICs from host %s", conf.HOST_0_NAME)
    conf.VDS_0_HOST.cache.clear()
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics


@attr(tier=2)
class TestSriovBase(NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    pf_obj = None

    @classmethod
    def teardown_class(cls):
        """
        Set number of VFs for PF to be 0
        """
        cls.pf_obj.set_number_of_vf(0)


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
    if rc:
        return False

    xml_obj = ElementTree.fromstring(xml_output)
    interfaces = xml_obj.find("devices").findall("interface")
    vlan_interface = filter(
        lambda x: x is not None, [i.find("vlan") for i in interfaces]
    )
    if not vlan_interface:
        raise conf.NET_EXCEPTION("VLAN not found on VM %s interfaces", vm)

    return vlan_interface[0].find("tag").get("id")
