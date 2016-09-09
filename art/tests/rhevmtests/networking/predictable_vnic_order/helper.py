#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for predictable vNIC order test
"""

import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as vnic_order_conf
import rhevmtests.networking.config as conf

logger = logging.getLogger("Predictable_vNIC_Order_Helper")


def add_vnics_to_vm():
    """
    Add vNICs to last VM

    :return: True if succeeded to add vNICs to last VM, False otherwise
    :rtype: bool
    """
    for vnic in vnic_order_conf.VNIC_NAMES:
        logger.info("Add %s to %s", vnic, vnic_order_conf.VM_NAME)
        if not ll_vms.addNic(
            positive=True, vm=vnic_order_conf.VM_NAME, name=vnic,
            network=conf.MGMT_BRIDGE
        ):
            return False
    return True


def get_vnics_names_and_macs_from_vm():
    """
    Get vNICs names and MACs of the VM

    :return: dict with vNICs names and MACs
    :rtype: dict
    """
    logger.info("Get %s nics", vnic_order_conf.VM_NAME)
    vm_nics = ll_vms.get_vm_nics_obj(vm_name=vnic_order_conf.VM_NAME)
    names_and_macs = dict()
    for vnic in vm_nics:
        vnic_name = vnic.get_name()
        logger.info("Get %s MAC address", vnic_name)
        mac = ll_vms.getVmMacAddress(
            positive=True, vm=vnic_order_conf.VM_NAME, nic=vnic_name
        )
        names_and_macs[vnic_name] = mac
    return names_and_macs
