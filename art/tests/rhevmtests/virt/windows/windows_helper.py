#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt windows helper
"""

import logging
from art.unittest_lib.common import testflow
from concurrent.futures import ThreadPoolExecutor
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.virt.config as virt_config
import config


logger = logging.getLogger(__name__)


def migrate_job_info():
    """
    builds kwargs dict for job_runner with
    vms name

    Returns:
        dict: dict with job info
    """
    kwargs_info = {}

    for vm_name in config.WINDOWS_VM_NAMES:
        kwargs_info['{0}'.format(vm_name)] = {
            'positive': True,
            'vm': vm_name
        }
    return kwargs_info


def test_vm_snapshots(vm_name, export_domain, with_memory=False):
    """
    Create, restore, export and remove snapshots

    Args:
        vm_name (str): vm_name
        with_memory (bool): create/restore snapshot with memory
        export_domain (str): export domain name

    Returns:
        bool: True if all actions success, else False
    """

    testflow.step("Create two new snapshots of vm %s", vm_name)
    for description in virt_config.SNAPSHOT_DESCRIPTION:
        job_description = "Creating VM Snapshot %s for VM %s" % (
            description, vm_name
        )
        logger.info("add snapshot job description: %s", job_description)
        if not ll_vms.addSnapshot(
            positive=True,
            vm=vm_name,
            description=description,
            persist_memory=with_memory
        ):
            logger.error("Failed to add snapshot to VM.")
            return False
    testflow.step(
        "Restore vm %s from snapshot %s",
        vm_name,
        virt_config.SNAPSHOT_DESCRIPTION[1]
    )
    if not ll_vms.restore_snapshot(
        True,
        vm=vm_name,
        description=virt_config.SNAPSHOT_DESCRIPTION[1],
        restore_memory=True,
        ensure_vm_down=True
    ):
        logger.error("Failed to restore snapshot.")
        return False
    testflow.step("Export vm %s with discarded snapshots", vm_name)
    if not ll_vms.exportVm(
        positive=True,
        vm=vm_name,
        storagedomain=export_domain,
        discard_snapshots='true',
        timeout=virt_config.VM_ACTION_TIMEOUT
    ):
        logger.error("Failed to export VM.")
        return False
    testflow.step(
        "Remove snapshots %s and %s of vm %s",
        virt_config.SNAPSHOT_DESCRIPTION[0],
        virt_config.SNAPSHOT_DESCRIPTION[1],
        vm_name
    )
    for snapshot in virt_config.SNAPSHOT_DESCRIPTION:
        if not ll_vms.removeSnapshot(
            positive=True,
            vm=vm_name,
            description=snapshot,
            timeout=config.VM_REMOVE_SNAPSHOT_TIMEOUT,
            wait=True
        ):
            logger.error("Failed to remove vm snapshot.")
            return False
    return True


def suspend_resume_vm(vm_name):
    """
    Suspend / Resume VM

    Args:
        vm_name (str): VM name
    """
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    )
    testflow.step("Suspend vm %s", vm_name)
    assert ll_vms.suspendVm(True, vm_name)
    testflow.step("Resume vm %s", vm_name)
    return ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    )


def wait_for_snapshot_jobs(vms_list, export_domain, with_memory=False):
    """
    Wait until all snapshot jobs finish and returns status

    Args:
        vms_list (list): vm names
        with_memory (bool): create/restore snapshot with memory
        export_domain (str): export domain name

    Returns:
        bool: True, if all snapshot jobs finish succeeded, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(vms_list)) as executor:
        for vm in vms_list:
            results.append(
                executor.submit(
                    test_vm_snapshots, vm, export_domain, with_memory
                )
            )
    for result in results:
        if not result.result():
            return False
    return True
