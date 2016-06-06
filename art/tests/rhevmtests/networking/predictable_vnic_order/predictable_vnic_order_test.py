#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Predictable vNIC order feature test cases
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import fixture_case01

logger = logging.getLogger("Predictable_vNIC_Order_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case01.__name__)
class TestPredictableVnicOrder01(NetworkTest):
    """
    Check vNICs order for new VM
    """
    __test__ = True

    @polarion("RHEVM3-4095")
    @bz({"1340648": {}})
    def test_check_vnics_order_vm(self):
        """
        Get vNICs names and MACs before start VM
        Start the VM
        Check vNICs MAC order
        """
        setup_dict = helper.get_vnics_names_and_macs_from_last_vm()
        self.assertTrue(
            ll_vms.startVm(
                positive=True, vm=conf.LAST_VM, wait_for_ip=True
            )
        )
        case_dict = helper.get_vnics_names_and_macs_from_last_vm()
        testflow.step("Check vNICs MAC ordering on VM %s", conf.LAST_VM)
        self.assertEqual(
            setup_dict, case_dict, "vNICs not in order on %s" % conf.LAST_VM
        )
