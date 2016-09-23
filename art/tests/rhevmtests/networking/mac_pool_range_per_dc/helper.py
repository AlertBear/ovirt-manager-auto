#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature helper
"""

import logging

from utilities import utils

import art.core_api.apis_exceptions as api_exc
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import config as conf
import rhevmtests.networking.config as network_conf

logger = logging.getLogger("MAC_Pool_Range_Per_cluster_Helper")


def update_mac_pool_range_size(
    mac_pool_name=conf.MAC_POOL_NAME_0, extend=True, size=(1, 1)
):
    """
    Update MAC pool range size for the first range in specific mac pool

    Args:
        mac_pool_name (str): Name of the MAC pool
        extend (bool): Extend or shrink the MAC pool range
        size (tuple, optional): Number to decrease from low MAC, number to
            add to high MAC

    Returns:
        bool: True if update succeeded, False if update failed
    """
    log = "Extend" if extend else "Shrink"
    logger.info("%s the MAC pool range by %s MAC", log, size[0] + size[1])
    mac_pool = ll_mac_pool.get_mac_pool(mac_pool_name)
    mac_pool_range = ll_mac_pool.get_mac_range_values(mac_pool)[0]
    low_mac = utils.MAC(mac_pool_range[0])
    high_mac = utils.MAC(mac_pool_range[1])
    if not hl_mac_pool.update_ranges_on_mac_pool(
        mac_pool_name=mac_pool_name, range_dict={
            mac_pool_range: (low_mac - size[0], high_mac + size[1])
        }
    ):
        logger.error(
            "Couldn't %s the MAC pool range for %s", log, mac_pool_name
        )
        return False
    return True


def check_single_mac_range_match(mac_ranges, start_idx, end_idx):
    """
    Check that MAC on the vNIC matches the MAC on the mac_ranges, where each
    range consists of a single MAC

    Args:
        mac_ranges (list): MAC ranges of MAC pool
        start_idx (int): Starting index for vNIC in vNIC list
        end_idx (int): Ending index for vNIC in vNIc list

    Returns:
        bool: True if there's a match, False if no match found
    """
    logger.info("Check that MACs on the VNICs correspond to Ranges")
    macs = [i[0] for i in mac_ranges]
    for i in range(start_idx, end_idx):
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=conf.MP_VM_0, nic=conf.NICS_NAME[i]
        )
        if nic_mac in macs:
            macs.remove(nic_mac)
        else:
            logger.error(
                "VNIC MAC %s is not in the MAC pool range for %s", nic_mac,
                conf.MAC_POOL_NAME_0
            )
            return False
    return True


def create_cluster_with_mac_pool(
    cluster_name=conf.EXT_CL_1, mac_pool_name=conf.MAC_POOL_NAME_0,
    mac_pool_ranges=list()
):
    """
    Create a new cluster with MAC pool

    Args:
        cluster_name (str): Cluster name
        mac_pool_name (str): MAC pool name
        mac_pool_ranges (list, optional): MAC pool ranges

    Returns:
        bool: True if cluster created successfully, False if cluster
            creation failed
    """
    if not mac_pool_name:
        mac_pool_obj = None
    else:
        try:
            mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
        except api_exc.EntityNotFound:
            ll_mac_pool.create_mac_pool(
                name=mac_pool_name, ranges=mac_pool_ranges
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)

    return ll_clusters.addCluster(
        positive=True, name=cluster_name,
        cpu=network_conf.CPU_NAME, mac_pool=mac_pool_obj,
        data_center=network_conf.DC_0
    )


def check_mac_in_range(
    vm=conf.MP_VM_0, nic=conf.NIC_NAME_1, mac_range=conf.MAC_POOL_RANGE_LIST[0]
):
    """
    Check if MAC of VM is in a specified range

    Args:
        vm (str, optional): VM name
        nic (str, optional): NIC of VM
        mac_range (tuple, optional): MAC Range

    Returns:
        bool: True if MAC is in range, False if MAC is not in range
    """
    logger.info(
        "Check that vNIC added to VM %s uses the correct MAC POOL value", vm
    )
    nic_mac = ll_vm.get_vm_nic_mac_address(vm=vm, nic=nic)
    if not nic_mac:
        logger.error("MAC was not found on NIC %s", conf.NIC_NAME_1)
        return False

    mac_range = utils.MACRange(mac_range[0], mac_range[1])
    if nic_mac not in mac_range:
        logger.error(
            "MAC %s is not in the MAC pool range  %s", nic_mac, mac_range
        )
        return False
    return True
