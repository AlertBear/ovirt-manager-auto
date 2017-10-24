#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for RunOnce test
"""
import copy

import pytest

import helper
import rhevmtests.helpers as gen_helper
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_storagedomains
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from rhevmtests.compute.virt import config


@pytest.fixture(scope="module")
def run_once_setup(request):
    """
    Base setup for run once test.
    1. Attach and activate iso domain.
    2. Fetch existing images from iso domain to use in the test.
    3. Create a vm for the test.
    """
    def fin():
        """
        Base teardown for run once test
        1. Detach and deactivate iso domain.
        2. Remove the test specific vm.
        """
        hl_storagedomains.detach_and_deactivate_domain(
            config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME,
            engine=config.ENGINE
        )
        ll_vms.removeVm(True, config.VM_RUN_ONCE)
    request.addfinalizer(fin)
    assert hl_storagedomains.attach_and_activate_domain(
        config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME
    )
    helper.set_iso_images_names()
    assert ll_vms.createVm(
        positive=True,
        vmName=config.VM_RUN_ONCE,
        vmDescription="run once vm",
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.STORAGE_NAME[0],
        provisioned_size=2 * config.GB, nic=config.NIC_NAME[0],
        memory=config.GB,
        max_memory=gen_helper.get_gb(4),
        network=config.MGMT_BRIDGE,
        os_type=config.VM_OS_TYPE,
        display_type=config.VM_DISPLAY_TYPE,
        type=config.VM_TYPE
    )


@pytest.fixture(scope='function')
def base_setup_fixture(request, run_once_setup):
    """
    Update parameters in vm if needed
    """
    args = request.node.get_marker("args_marker")
    params = args.kwargs if args else {}

    def fin():
        """
        Finalizer for base run once test case - stops vm
        """
        ll_vms.stop_vms_safely([config.VM_RUN_ONCE])
    request.addfinalizer(fin)
    update_params = copy.deepcopy(config.RUN_ONCE_VM_PARAMS)
    for key, val in params.iteritems():
        update_params[key] = val
    assert ll_vms.updateVm(
        True, config.VM_RUN_ONCE,
        **update_params
    )


@pytest.fixture(scope='function')
def image_provider_fixture(request):
    """
    Check that the test case has the correct image/s to use
    """
    args = request.node.get_marker("images_marker")
    images = args if args else []
    for image in images:
        assert image, config.ISO_ERROR % config.SHARED_ISO_DOMAIN_NAME


@pytest.fixture(scope='function')
def remove_vm_disk_fixture(request):
    """
    Removes vm disk before test case
    """
    def fin():
        """
        Creates a disk for the vm to be used after test case
        """
        ll_vms.addDisk(
            True, config.VM_RUN_ONCE, 2 * config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )
    request.addfinalizer(fin)
    disk = ll_vms.getVmDisks(config.VM_RUN_ONCE)[0].name
    assert ll_vms.removeDisk(True, config.VM_RUN_ONCE, disk)


@pytest.fixture(scope='function')
def remove_vm_nic_fixture(request):
    """
    Removes vm nic before test case
    """
    def fin():
        """
        Add a nic to the vm to be used after the test case
        """
        ll_vms.addNic(
            True, config.VM_RUN_ONCE,
            name=config.NIC_NAME[0], network=config.MGMT_BRIDGE
        )
    request.addfinalizer(fin)
    assert ll_vms.removeNic(True, config.VM_RUN_ONCE, config.NIC_NAME[0])
