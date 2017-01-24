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
from fixtures import (
    update_vms_nics_stats, vm_prepare_setup, host_vm_prepare_setup
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    host_vm_prepare_setup.__name__,
    setup_networks_fixture.__name__,
    vm_prepare_setup.__name__,
    update_vms_nics_stats.__name__
)
class TestCumulativeNetworkUsageVmStatisticsCase01(NetworkTest):
    """
    1) Change the vNIC profile to conf.NETWORK_2.
    2) Change the vNIC profile to <empty network>.
    3) Hot unplug the vNIC.
    4) Hot plug the vNIC.
    """
    # vm_prepare_setup
    nic_name = rx_tx_conf.VM_NIC_NAME
    net_1 = rx_tx_conf.NETWORK_1
    net_2 = rx_tx_conf.NETWORK_2

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 1,
                "network": net_2
            },
        },
        1: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 1,
                "network": net_2
            },
        }
    }

    @pytest.mark.parametrize(
        "update_nic_dict",
        [
            polarion("RHEVM3-13580")(rx_tx_conf.UPDATE_NIC.get("case_vm_1")),
            polarion("RHEVM3-13581")(rx_tx_conf.UPDATE_NIC.get("case_vm_2")),
            polarion("RHEVM3-6639")(rx_tx_conf.UPDATE_NIC.get("case_vm_3")),
            polarion("RHEVM3-13512")(rx_tx_conf.UPDATE_NIC.get("case_vm_4")),
        ]
    )
    def test_update_nic(self, update_nic_dict):
        """
        1) Change the vNIC network to conf.NETWORK_2.
        2) Attach the vNIC to <empty network>.
        3) Hot unplug the vNIC.
        4) Hot plug the vNIC.
        """
        testflow.step(update_nic_dict.pop("logger"))
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_1, nic=self.nic_name, **update_nic_dict
        )
        testflow.step("Check that statistics remains the same")
        assert helper.compare_nic_stats(
            nic=self.nic_name, vm=conf.VM_1, total_rx=rx_tx_conf.TOTAL_RX,
            total_tx=rx_tx_conf.TOTAL_TX
        )
