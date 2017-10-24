#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt test - RNG device
"""
import pytest

import config
import fixtures as hwrng_fixtures
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    testflow,
    common,
)
from rhevmtests.compute.virt.fixtures import (
    start_vms, update_vm
)


class TestUrandom(common.VirtTest):
    """
    Urandom RNG Device Class
    """
    vm_name = config.VM_NAME[0]
    update_vm_params = {
        'rng_device': config.URANDOM_RNG
    }
    wait_for_vms_ip = False

    @tier2
    @pytest.mark.usefixtures(update_vm.__name__, start_vms.__name__,)
    @polarion("RHEVM-19286")
    def test_urandom(self):
        """
        Set VM urandom device, and verify VM was set properly
        """
        testflow.step(
            "Verify that device %s exists on vm %s",
            self.update_vm_params['rng_device'], self.vm_name
        )
        assert helper.check_if_device_exists(
            vm_name=self.vm_name,
            device_name=self.update_vm_params['rng_device']
        )


class TestHwrng(common.VirtTest):
    """
    Hwrng RNG Device Class
    """
    vm_name = config.VM_NAME[0]
    wait_for_vms_ip = False
    update_vm_params = {
        'rng_device': config.HW_RNG
    }

    @tier2
    @polarion("RHEVM3-6485")
    @pytest.mark.usefixtures(
        hwrng_fixtures.enable_hwrng_source_on_cluster.__name__,
        update_vm.__name__,
        start_vms.__name__,
        hwrng_fixtures.add_symbolic_link_on_host.__name__
    )
    def test_hwrng(self):
        """
        Set VM hwrng device, and verify VM was set properly
        """
        testflow.step(
            "Verify that device %s exists on vm %s",
            self.update_vm_params['rng_device'], self.vm_name
        )
        assert helper.check_if_device_exists(
            vm_name=self.vm_name,
            device_name=self.update_vm_params['rng_device']
        )
