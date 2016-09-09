#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Predictable vNIC order feature test cases
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as vnic_order_conf
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import prepare_setup_predictable_vnic_order
import rhevmtests.networking.config as conf

logger = logging.getLogger("Predictable_vNIC_Order_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(prepare_setup_predictable_vnic_order.__name__)
class TestPredictableVnicOrder01(NetworkTest):
    """
    Check vNICs order for new VM
    """
    __test__ = True
    vm = vnic_order_conf.VM_NAME

    @polarion("RHEVM3-4095")
    def test_check_vnics_order_vm(self):
        """
        Get vNICs names and MACs before start VM
        Start the VM
        Check vNICs MAC order
        """
        setup_dict = helper.get_vnics_names_and_macs_from_vm()
        assert ll_vms.startVm(
            positive=True, vm=self.vm, wait_for_status=conf.VM_UP
        )
        case_dict = helper.get_vnics_names_and_macs_from_vm()
        testflow.step("Check vNICs MAC ordering on VM %s", self.vm)
        assert setup_dict == case_dict, "vNICs not in order on %s" % self.vm
