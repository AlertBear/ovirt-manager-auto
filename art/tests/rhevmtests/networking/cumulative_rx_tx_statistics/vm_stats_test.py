#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for VM
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import rx_tx_stat_vm_case01

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(rx_tx_stat_vm_case01.__name__)
class CumulativeNetworkUsageVmStatisticsCase1(NetworkTest):
    """
    Hot unplug the vNIC
    Hot plug the vNIC
    Change the vNIC profile to conf.NETWORK_2
    Change the vNIC profile to <empty network>
    """
    __test__ = True

    @polarion("RHEVM3-13580")
    def test_01_change_vnic_profile(self):
        """
        Change the vNIC network to conf.NETWORK_2
        """
        profile_dict = {
            "network": conf.NETWORK_2
        }
        testflow.step("Change %s profile to %s", conf.VM_NIC_1, conf.NETWORK_2)
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=conf.VM_1, nic=conf.VM_NIC_1, **profile_dict
            )
        )
        testflow.step("Check that statistics remains the same")
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.VM_NIC_1, vm=conf.VM_1, total_rx=conf.TOTAL_RX,
                total_tx=conf.TOTAL_TX
            )
        )

    @polarion("RHEVM3-13581")
    def test_02_change_vnic_to_empty_network(self):
        """
        Attach the vNIC to <empty network>
        """
        profile_dict = {
            "network": None
        }
        testflow.step("Change %s to empty profile", conf.VM_NIC_1)
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=conf.VM_1, nic=conf.VM_NIC_1, **profile_dict
            )
        )
        testflow.step("Check that statistics remains the same")
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.VM_NIC_1, vm=conf.VM_1, total_rx=conf.TOTAL_RX,
                total_tx=conf.TOTAL_TX
            )
        )

    @polarion("RHEVM3-6639")
    def test_03_hot_unplug_vnic(self):
        """
        Hot unplug the vNIC
        """
        testflow.step("Unplug vNIC %s from VM %s", conf.VM_NIC_1, conf.VM_1)
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=conf.VM_1, nic=conf.VM_NIC_1, plugged=False
            )
        )
        testflow.step("Check that statistics remains the same")
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.VM_NIC_1, vm=conf.VM_1, total_rx=conf.TOTAL_RX,
                total_tx=conf.TOTAL_TX
            )
        )

    @polarion("RHEVM3-13512")
    def test_04_hot_plug_vnic(self):
        """
        Hot plug the vNIC
        """
        testflow.step("Plug vNIC %s to VM %s", conf.VM_NIC_1, conf.VM_1)
        self.assertTrue(
            ll_vms.updateNic(
                positive=True, vm=conf.VM_1, nic=conf.VM_NIC_1, plugged=True
            )
        )
        testflow.step("Check that statistics remains the same")
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.VM_NIC_1, vm=conf.VM_1, total_rx=conf.TOTAL_RX,
                total_tx=conf.TOTAL_TX
            )
        )
