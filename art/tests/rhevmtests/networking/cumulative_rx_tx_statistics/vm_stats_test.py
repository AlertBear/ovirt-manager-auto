#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for VM
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as rx_tx_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import update_vms_nics_stats, vm_prepare_setup


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    vm_prepare_setup.__name__,
    update_vms_nics_stats.__name__
)
class TestCumulativeNetworkUsageVmStatisticsCase1(NetworkTest):
    """
    Hot unplug the vNIC
    Hot plug the vNIC
    Change the vNIC profile to conf.NETWORK_2
    Change the vNIC profile to <empty network>
    """
    __test__ = True
    nic_name = rx_tx_conf.VM_NIC_NAME

    @polarion("RHEVM3-13580")
    def test_01_change_vnic_profile(self):
        """
        Change the vNIC network to conf.NETWORK_2
        """

        profile_dict = {
            "network": rx_tx_conf.NETWORK_2
        }
        testflow.step(
            "Change %s profile to %s", self.nic_name, rx_tx_conf.NETWORK_2
        )
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_1, nic=self.nic_name, **profile_dict
        )
        testflow.step("Check that statistics remains the same")
        assert helper.compare_nic_stats(
            nic=self.nic_name, vm=conf.VM_1, total_rx=rx_tx_conf.TOTAL_RX,
            total_tx=rx_tx_conf.TOTAL_TX
        )

    @polarion("RHEVM3-13581")
    def test_02_change_vnic_to_empty_network(self):
        """
        Attach the vNIC to <empty network>
        """
        profile_dict = {
            "network": None
        }
        testflow.step("Change %s to empty profile", self.nic_name)
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_1, nic=self.nic_name, **profile_dict
        )
        testflow.step("Check that statistics remains the same")
        assert helper.compare_nic_stats(
            nic=self.nic_name, vm=conf.VM_1, total_rx=rx_tx_conf.TOTAL_RX,
            total_tx=rx_tx_conf.TOTAL_TX
        )

    @polarion("RHEVM3-6639")
    def test_03_hot_unplug_vnic(self):
        """
        Hot unplug the vNIC
        """
        testflow.step("Unplug vNIC %s from VM %s", self.nic_name, conf.VM_1)
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_1, nic=self.nic_name, plugged=False
        )
        testflow.step("Check that statistics remains the same")
        assert helper.compare_nic_stats(
            nic=self.nic_name, vm=conf.VM_1, total_rx=rx_tx_conf.TOTAL_RX,
            total_tx=rx_tx_conf.TOTAL_TX
        )

    @polarion("RHEVM3-13512")
    def test_04_hot_plug_vnic(self):
        """
        Hot plug the vNIC
        """
        testflow.step("Plug vNIC %s to VM %s", self.nic_name, conf.VM_1)
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_1, nic=self.nic_name, plugged=True
        )
        testflow.step("Check that statistics remains the same")
        assert helper.compare_nic_stats(
            nic=self.nic_name, vm=conf.VM_1, total_rx=rx_tx_conf.TOTAL_RX,
            total_tx=rx_tx_conf.TOTAL_TX
        )
