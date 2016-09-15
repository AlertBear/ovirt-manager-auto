#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for topologies job
"""

import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking import config

logger = logging.getLogger("topologies_helper")

TIMEOUT = 300


def update_vnic_driver(driver, vnic_profile):
    """
    Update vNIC driver for VM

    :param driver: driver to update the vNIC (virtio, e1000, rtl8139)
    :type driver: str
    :param vnic_profile: vnic_profile name
    :type vnic_profile: str
    :return: True in case of success/False otherwise
    :rtype: bool
    """
    if not ll_vms.updateNic(
        positive=True, vm=config.VM_0, nic=config.VM_NIC_0,
        plugged=False, vnic_profile=vnic_profile, network=vnic_profile
    ):
        return False

    if not ll_vms.updateNic(
        positive=True, vm=config.VM_0, nic=config.VM_NIC_0,
        interface=driver, plugged=True, vnic_profile=vnic_profile,
        network=vnic_profile
    ):
        return False
    return True


def check_connectivity(vm=True, flags=None):
    """
    Check connectivity for VM and non-VM networks

    :param vm: Check connectivity to VM network if True, False for non-VM
    :type vm: bool
    :param flags: extra flags for ping command (for example -I eth1)
    :type flags: str
    :return: True in case of success/False otherwise
    :rtype: bool
    """
    if vm:
        ip = ll_vms.waitForIP(vm=config.VM_0, timeout=TIMEOUT)
        return ip[0]

    return network_helper.send_icmp_sampler(
        host_resource=config.VDS_0_HOST, dst=config.DST_HOST_IP,
        extra_args=flags
    )


def check_connectivity_log(
        driver=None, mode=None, error=False, vlan=False
):
    """
    Generate string for info/errors.

    :param driver: driver of the interface
    :type driver: str
    :param mode: Bond mode
    :type mode: int
    :param error: error string is True
    :type error: bool
    :param vlan: vlan network in string is True
    :type vlan: bool
    :return: output message
    :rtype: str

    """
    interface = "BOND mode %s" % mode if mode else ""
    vlan_info = "VLAN over" if vlan else ""
    driver_info = "with %s driver" % driver if driver else ""
    output = "Check connectivity %s to %s %s network %s" % (
        "failed" if error else "", vlan_info, interface, driver_info
    )
    return output


def check_vm_connect_and_log(
    driver=None, mode=None, vlan=False, vm=True, flags=None
):
    """
    Check VM connectivity with logger info and raise error if fails

    :param driver: driver of the interface
    :type driver: str
    :param mode: Bond mode
    :type mode: int
    :param vlan: ping from host if True else ping from engine
    :type vlan: bool
    :param vm: Check connectivity to VM network if True, False for non-VM
    :type vm: bool
    :param flags: extra flags for ping command (for example -I eth1)
    :type flags: str
    :return: True or raise exception
    :rtype: bool
    """
    logger.info(
        check_connectivity_log(
            mode=mode, driver=driver, vlan=vlan
        )
    )
    if not check_connectivity(vm=vm, flags=flags):
        logger.error(
            check_connectivity_log(
                mode=mode, driver=driver, error=True, vlan=vlan
            )
        )
        return False
    return True
