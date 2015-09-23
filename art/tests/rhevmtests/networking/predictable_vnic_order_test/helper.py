#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for predictable vNIC order test
"""

import logging
import config as conf
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger("Predictable_vNIC_Order_Helper")


def seal_vm_and_remove_vnics():
    """
    Seal VM and remove all vNICs

    :return: True/False
    :rtype: bool
    """
    logger.info("Sealing %s", conf.VM_NAME)
    if not net_help.seal_vm(vm=conf.VM_NAME, root_password=conf.VMS_LINUX_PW):
        logger.error("Failed to seal %s", conf.VM_NAME)
        return False

    vm_nics = ll_vms.get_vm_nics_obj(vm_name=conf.VM_NAME)
    for vnic in vm_nics:
        vnic_name = vnic.get_name()
        logger.info("Remove %s from %s", vnic_name, conf.VM_NAME)
        if not ll_vms.removeNic(positive=True, vm=conf.VM_NAME, nic=vnic_name):
            logger.error(
                "Failed to remove %s from %s", vnic_name, conf.VM_NAME
            )
            return False
    return True


def add_vnics_to_vm():
    """
    Add vNICs to VM

    :raise: conf.NET_EXCEPTION
    """
    for i in range(4):
        logger.info("Add %s to %s", conf.NIC_NAME[i], conf.VM_NAME)
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_NAME, name=conf.NIC_NAME[i],
            network=conf.MGMT_BRIDGE
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add %s to %s" % (conf.NIC_NAME[i], conf.VM_NAME)
            )


def get_vnics_names_and_macs():
    """
    Get VM vNICs names and MACs

    :return: dict with vNICs names and MACs
    :rtype: dict
    """
    logger.info("Get %s nics", conf.VM_NAME)
    vm_nics = ll_vms.get_vm_nics_obj(vm_name=conf.VM_NAME)
    names_and_macs = dict()
    for vnic in vm_nics:
        vnic_name = vnic.get_name()
        logger.info("Get %s MAC address", vnic_name)
        mac = ll_vms.getVmMacAddress(
            positive=True, vm=conf.VM_NAME, nic=vnic_name
        )
        names_and_macs[vnic_name] = mac
    return names_and_macs
