#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature helper
"""

import logging
import config as conf
import rhevmtests.networking.config as network_conf
from utilities import utils
import art.core_api.apis_exceptions as api_exc
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Helper")


def update_mac_pool_range_size(
    mac_pool_name=conf.MAC_POOL_NAME_0, extend=True, size=(1, 1)
):
    """
    Update MAC pool range size for the first range in specific mac pool

    :param mac_pool_name: Name of the MAC pool
    :type mac_pool_name: str
    :param extend: Extend or shrink the MAC pool range
    :type extend: bool
    :param size: (number to decrease from low MAC, number to add to high MAC)
    :type size: tuple
    :return: True/False
    :rtype: bool
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

    :param mac_ranges: MAC ranges of MAC pool
    :type mac_ranges: list
    :param start_idx: Starting index for vNIC in vNIC list
    :type start_idx: int
    :param end_idx: Ending index for vNIC in vNIc list
    :type end_idx: int
    :return : True/False
    :rtype: bool
    """
    logger.info("Check that MACs on the VNICs correspond to Ranges")
    macs = [i[0] for i in mac_ranges]
    for i in range(start_idx, end_idx):
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=network_conf.VM_0, nic=network_conf.NIC_NAME[i]
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


def create_dc(
    dc_name=network_conf.EXT_DC_1, mac_pool_name=conf.MAC_POOL_NAME_0,
    mac_pool_ranges=list(), version=network_conf.COMP_VERSION
):
    """
    Create a new DC with MAC pool

    :param dc_name: DC name
    :type dc_name: str
    :param mac_pool_name: MAC pool name
    :type mac_pool_name: str
    :param mac_pool_ranges: MAC pool ranges
    :type mac_pool_ranges: list
    :param version: Version of DC
    :type version: str
    :raise :NetworkException
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

    assert ll_dc.addDataCenter(
        positive=True, name=dc_name,
        storage_type=network_conf.STORAGE_TYPE, version=version,
        local=False, mac_pool=mac_pool_obj
    )


def check_mac_in_range(
    vm=conf.MP_VM, nic=conf.NIC_NAME_1,
    mac_range=network_conf.MAC_POOL_RANGE_LIST[0]
):
    """
    Check if MAC of VM is in the given range

    :param vm: VM name
    :type vm: str
    :param nic: NIC of VM
    :type nic: str
    :param mac_range: MAC Range
    :type mac_range: tuple
    :return :True/False
    :rtype: bool
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
