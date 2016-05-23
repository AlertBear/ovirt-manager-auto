#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for predictable vNIC order test
"""

import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help

logger = logging.getLogger("Predictable_vNIC_Order_Helper")


def seal_last_vm_and_remove_vnics():
    """
    Seal last VM and remove all vNICs

    :return: True if succeeded to seal last VM and remove all vNICs,
        False otherwise
    :rtype: bool
    """
    logger.info("Sealing %s", conf.LAST_VM)
    if not net_help.seal_vm(vm=conf.LAST_VM, root_password=conf.VMS_LINUX_PW):
        logger.error("Failed to seal %s", conf.LAST_VM)
        return False

    vm_nics = ll_vms.get_vm_nics_obj(vm_name=conf.LAST_VM)
    for vnic in vm_nics:
        vnic_name = vnic.get_name()
        logger.info("Remove %s from %s", vnic_name, conf.LAST_VM)
        if not ll_vms.removeNic(positive=True, vm=conf.LAST_VM, nic=vnic_name):
            logger.error(
                "Failed to remove %s from %s", vnic_name, conf.LAST_VM
            )
            return False
    return True


def add_vnics_to_vm():
    """
    Add vNICs to last VM

    :return: True if succeeded to add vNICs to last VM, False otherwise
    :rtype: bool
    """
    for i in range(4):
        logger.info("Add %s to %s", conf.NIC_NAME[i], conf.LAST_VM)
        if not ll_vms.addNic(
            positive=True, vm=conf.LAST_VM, name=conf.NIC_NAME[i],
            network=conf.MGMT_BRIDGE
        ):
            return False
    return True


def get_vnics_names_and_macs_from_last_vm():
    """
    Get vNICs names and MACs of the last VM

    :return: dict with vNICs names and MACs
    :rtype: dict
    """
    logger.info("Get %s nics", conf.LAST_VM)
    vm_nics = ll_vms.get_vm_nics_obj(vm_name=conf.LAST_VM)
    names_and_macs = dict()
    for vnic in vm_nics:
        vnic_name = vnic.get_name()
        logger.info("Get %s MAC address", vnic_name)
        mac = ll_vms.getVmMacAddress(
            positive=True, vm=conf.LAST_VM, nic=vnic_name
        )
        names_and_macs[vnic_name] = mac
    return names_and_macs
