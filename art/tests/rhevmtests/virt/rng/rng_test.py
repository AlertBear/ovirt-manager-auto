#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt test - RNG device
"""
import config
import helper
import pytest
from art.unittest_lib import testflow, common, attr
from art.test_handler.tools import polarion
from rhevmtests.virt.fixtures import start_vms
from rhevmtests.virt.rng.fixtures import (
    enable_rng_on_vm, enable_hwrng_source_on_cluster, update_vm_host
)


class TestUrandom(common.VirtTest):
    """
    Urandom RNG Device Class
    """
    vm_name = config.VM_NAME[0]
    rng_device = config.URANDOM_RNG

    @attr(tier=2)
    @pytest.mark.usefixtures(enable_rng_on_vm.__name__, start_vms.__name__,)
    @polarion("RHEVM-19286")
    def test_urandom(self):
        """
        Set VM urandom device, and verify VM was set properly
        """
        testflow.step(
            "Verify that device %s exists on vm %s",
            self.rng_device, self.vm_name
        )
        assert helper.check_if_device_exists(self.vm_name, self.rng_device)


class TestHwrng(common.VirtTest):
    """
    Hwrng RNG Device Class
    """
    vm_name = config.VM_NAME[0]
    rng_device = config.HW_RNG

    @attr(tier=2)
    @polarion("RHEVM3-6485")
    @pytest.mark.usefixtures(
        update_vm_host.__name__,
        enable_hwrng_source_on_cluster.__name__,
        enable_rng_on_vm.__name__, start_vms.__name__
    )
    def test_hwrng(self):
        """
        Set VM hwrng device, and verify VM was set properly
        """
        testflow.step(
            "Verify that device %s exists on vm %s",
            self.rng_device, self.vm_name
        )
        assert helper.check_if_device_exists(self.vm_name, self.rng_device)
