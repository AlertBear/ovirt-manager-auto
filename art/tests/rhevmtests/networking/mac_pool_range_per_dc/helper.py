#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature helper
"""
import logging
import config as conf
import utilities.utils as utils
import art.core_api.apis_exceptions as api_exc
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Helper")


def create_mac_pool(
    mac_pool_name=conf.MAC_POOL_NAME_0, mac_pool_ranges=list(), positive=True,
    allow_duplicates=False
):
    """
    Create MAC pool with MAC pool range

    :param mac_pool_name: Name of the MAC pool
    :type mac_pool_name: str
    :param mac_pool_ranges: List of ranges for the MAC pool
    :type mac_pool_ranges: list
    :param positive: Expected result
    :type positive: bool
    :raise: NetworkException
    """
    log = "Cannot" if positive else "Can"
    mac_pool_ranges = (
        [
            conf.MAC_POOL_RANGE_LIST[0]
        ] if not mac_pool_ranges else mac_pool_ranges
    )
    logger.info("Create MAC pool %s", mac_pool_name)
    status = ll_mac_pool.create_mac_pool(
        name=mac_pool_name,
        ranges=mac_pool_ranges, allow_duplicates=allow_duplicates
    )
    if status != positive:
        raise conf.NET_EXCEPTION(
            "%s create new MAC pool %s" % (log, mac_pool_name)
        )


def update_dc_with_mac_pool(
    dc=conf.DC_NAME[0], mac_pool_name=conf.MAC_POOL_NAME_0, teardown=False
):
    """
    Update DC with MAC pool

    :param dc: Name of the DC to update with MAC pool
    :type dc: str
    :param mac_pool_name: Name of the MAC pool
    :type mac_pool_name: str
    :param teardown: flag if function run in teardown
    :type teardown: bool
    :raise: NetworkException
    """
    log_error = "Couldn't update DC %s with MAC pool %s"
    logger.info(
        "Update the DC %s with MAC pool %s", dc, mac_pool_name
    )
    if not ll_dc.updateDataCenter(
        True, datacenter=dc,
        mac_pool=ll_mac_pool.get_mac_pool(mac_pool_name)
    ):
        if teardown:
            logger.info(log_error, dc, mac_pool_name)
            TestCase.test_failed = True
        else:
            raise conf.NET_EXCEPTION(log_error % (dc, mac_pool_name))


def remove_mac_pool(mac_pool_name=conf.MAC_POOL_NAME_0):
    """
    Remove MAC pool

    :param mac_pool_name: MAC pool name
    :type mac_pool_name: str
    """
    logger.info("Remove MAC pool %s ", mac_pool_name)
    if not ll_mac_pool.remove_mac_pool(mac_pool_name):
        logger.error(
            "Couldn't remove MAC pool %s", mac_pool_name
        )
        TestCase.test_failed = True


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
    :raise: NetworkException
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
        raise conf.NET_EXCEPTION(
            "Couldn't %s the MAC pool range for %s" % (log, mac_pool_name)
        )


def add_nic(positive=True, vm=conf.VM_NAME[0], name=conf.NIC_NAME_1, **kwargs):
    """
    Add NIC to VM

    :param positive: Expected result
    :type positive: bool
    :param vm: name of the VM to add NIC to
    :type vm: str
    :param name: NIC to add to VM
    :type name: str
    :param kwargs: dictionary of parameters when adding a new NIC
    :type kwargs: dict
    :raise: NetworkException
    """
    status_log = "Failed" if positive else "Succeeded"
    mac_log = " with manual MAC" if kwargs.get("mac_address") else "from pool"
    logger.info("Adding %s to %s %s", name, vm, mac_log)
    if not ll_vm.addNic(positive=positive, vm=vm, name=name, **kwargs):
        raise conf.NET_EXCEPTION(
            "%s to add %s to %s %s" % (status_log, name, vm, mac_log)
        )


def remove_nic(vm=conf.VM_NAME[0], nic=conf.NIC_NAME_1):
    """
    Remove vNIC from VM

    :param vm: name of the VM to add NIC to
    :type vm: str
    :param nic: NIC to add to VM
    :type nic: str
    :raise: NetworkException
    """
    try:
        ll_vm.removeNic(True, vm=vm, nic=nic)
    except api_exc.EntityNotFound:
        logger.error("Couldn't remove VNIC %s from VM", nic)
        TestCase.test_failed = True


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
    :raise :NetworkException
    """
    logger.info("Check that MACs on the VNICs correspond to Ranges")
    macs = [i[0] for i in mac_ranges]
    for i in range(start_idx, end_idx):
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=conf.VM_NAME[0], nic=conf.NIC_NAME[i]
        )
        if nic_mac in macs:
            macs.remove(nic_mac)
        else:
            raise conf.NET_EXCEPTION(
                "VNIC MAC %s is not in the MAC pool range for %s" %
                (nic_mac, conf.MAC_POOL_NAME_0)
            )


def create_dc(
    dc_name=conf.EXT_DC_1, mac_pool_name=conf.MAC_POOL_NAME_0,
    mac_pool_ranges=list(), version=conf.COMP_VERSION
):
    """
    Create a new DC with MAC pool

    :param dc_name: DC name
    :type dc_name: str
    :param mac_pool_name: MAC pool name
    :type mac_pool_name: str
    :param mac_pool_ranges: MAC pool ranges
    :type mac_pool_ranges: list
    :raise :NetworkException
    """
    if not mac_pool_name:
        mac_pool_obj = None
        mac_pool_name = "Default"
    else:
        try:
            mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
        except api_exc.EntityNotFound:
            create_mac_pool(
                mac_pool_name=mac_pool_name, mac_pool_ranges=mac_pool_ranges
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)

    logger.info("Create a new DC with %s", mac_pool_name)
    if not ll_dc.addDataCenter(
        positive=True, name=dc_name,
        storage_type=conf.STORAGE_TYPE, version=version,
        local=False, mac_pool=mac_pool_obj
    ):
        raise conf.NET_EXCEPTION("Couldn't add a DC %s to the setup" % dc_name)


def remove_dc(dc_name=conf.EXT_DC_1, teardown=True):
    """
    Remove DC

    :param dc_name: DC name
    :type dc_name: str
    :param teardown: flag if function run in teardown
    :type teardown: bool
    :raise :NetworkException
    """
    log_error = "Failed to remove DC %s"
    logger.info("Remove a DC %s", dc_name)
    if not ll_dc.removeDataCenter(
        positive=True, datacenter=dc_name
    ):
        if teardown:
            logger.error(log_error, dc_name)
            TestCase.test_failed = True
        else:
            raise conf.NET_EXCEPTION(log_error, dc_name)


def check_mac_in_range(
    vm=conf.MP_VM, nic=conf.NIC_NAME_1, mac_range=conf.MAC_POOL_RANGE_LIST[0]
):
    """
    Check if MAC of VM is in the given range

    :param vm: VM name
    :type vm: str
    :param nic: NIC of VM
    :type nic: str
    :param mac_range: MAC Range
    :type mac_range: tuple
    :raise :NetworkException
    """
    logger.info(
        "Check that vNIC added to VM %s uses the correct MAC POOL value", vm
    )

    nic_mac = ll_vm.get_vm_nic_mac_address(vm=vm, nic=nic)
    if not nic_mac:
        raise conf.NET_EXCEPTION(
            "MAC was not found on NIC %s" % conf.NIC_NAME_1
        )
    mac_range = utils.MACRange(mac_range[0], mac_range[1])
    if nic_mac not in mac_range:
        raise conf.NET_EXCEPTION(
            "MAC %s is not in the MAC pool range  %s" % (nic_mac, mac_range)
        )
