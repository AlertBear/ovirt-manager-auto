#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature helper
"""

import logging

import art.core_api.apis_exceptions as api_exc
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import config as conf
import rhevmtests.config as global_conf
import rhevmtests.networking.config as network_conf
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    jobs as ll_jobs,
    mac_pool as ll_mac_pool,
    vms as ll_vm
)
from art.rhevm_api.utils import test_utils
from utilities import utils

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


def check_single_mac_range_match(vm, vm_vnics, mac_ranges):
    """
    Check that MAC on the vNIC matches the MAC on the mac_ranges, where each
    range consists of a single MAC

    Args:
        vm: (str): VM name
        vm_vnics (dict): VM vNICs
        mac_ranges (list): MAC ranges of MAC pool

    Returns:
        bool: True if there's a match, False if no match found
    """
    logger.info("Check that MACs on the VNICs correspond to Ranges")
    macs = [i[0] for i in mac_ranges]

    for vnic in vm_vnics:
        vm_nic_mac = ll_vm.get_vm_nic_mac_address(vm=vm, nic=vnic)
        if vm_nic_mac in macs:
            macs.remove(vm_nic_mac)
        else:
            logger.error(
                "VNIC MAC %s is not in the MAC pool range for %s", vm_nic_mac,
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


def check_mac_in_range(vm, nic, mac_range=conf.MAC_POOL_RANGE_LIST[0]):
    """
    Check if MAC of VM is in a specified range

    Args:
        vm (str): VM name
        nic (str): NIC of VM
        mac_range (tuple): MAC Range

    Returns:
        bool: True if MAC is in range, False otherwise
    """
    logger.info(
        "Check that vNIC added to VM %s uses the correct MAC POOL value", vm
    )
    nic_mac = ll_vm.get_vm_nic_mac_address(vm=vm, nic=nic)
    if not nic_mac:
        logger.error("MAC was not found on NIC %s", nic)
        return False

    mac_range = utils.MACRange(mac_range[0], mac_range[1])
    if nic_mac not in mac_range:
        logger.error(
            "MAC %s is not in the MAC pool range  %s", nic_mac, mac_range
        )
        return False
    return True


def shutdown_stateless_vm(vm, dc):
    """
    Shutdown a VM and wait for snapshot completion

    Args:
        vm (str): VM to stop
        dc (str): Data-Center name where the VM resides

    Returns:
        bool: True for success, False for failure
    """
    if not ll_vm.stop_vms_safely(vms_list=[vm]):
        return False

    return not test_utils.wait_for_tasks(
        engine=network_conf.ENGINE, datacenter=dc
    )


def preview_snapshot_on_vm(vm, snapshot_desc, positive=True):
    """
    Preview snapshot of VM

    NOTE: Function shuts down the VM

    Args:
        vm (str): VM name
        snapshot_desc (str): Snapshot description to preview
        positive (bool): True for positive test, False for negative test

    Returns:
        bool: True for success, False for failure
    """
    # Asynchronous API call to preview a snapshot (creates background task)
    res_preview_snapshot = ll_vm.preview_snapshot(
        positive=positive, vm=vm, description=snapshot_desc,
        ensure_vm_down=True
    )
    # Return on failure of asynchronous call (no background job is created)
    # This is relevant for positive and negative tests
    if not res_preview_snapshot:
        return False

    # Wait for snapshot task to be completed
    ll_jobs.wait_for_jobs(job_descriptions=[global_conf.JOB_PREVIEW_SNAPSHOT])

    desired_job_status = (
        global_conf.JOB_FINISHED if positive else global_conf.JOB_FAILED
    )
    return ll_jobs.check_recent_job(
        description=global_conf.JOB_PREVIEW_SNAPSHOT,
        job_status=desired_job_status
    )[0]


def remove_non_default_mac_pools():
    """
    Remove non-default MAC pools from engine

    Returns:
        bool: True if all non-default MAC pools removed successfully, False
            otherwise
    """
    res_list = []
    all_macs = ll_mac_pool.get_all_mac_pools()
    for mac in filter(lambda x: x.name != "Default", all_macs):
        try:
            res = ll_mac_pool.remove_mac_pool(mac_pool_name=mac.name)
        except Exception as e:
            logger.error(e)
            res_list.append(False)
        else:
            res_list.append(res)
    return all(res_list)


def undo_snapshot_and_wait(vm, snapshot_desc):
    """
    Undo a snapshot and wait for snapshot and job completion

    Args:
        vm (str): VM name
        snapshot_desc (str): Snapshot description to wait for

    Returns:
        bool: True for undo success, False for failure
    """
    if ll_vm.undo_snapshot_preview(positive=True, vm=vm, ensure_vm_down=True):
        ll_jobs.wait_for_jobs([global_conf.JOB_RESTORE_SNAPSHOT])
        ll_vm.wait_for_vm_snapshots(
            vm_name=vm, states=global_conf.SNAPSHOT_OK,
            snapshots_description=[snapshot_desc]
        )
        return True
    return False
