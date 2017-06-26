#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""

import pytest

import config as rx_tx_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    send_icmp, update_host_nics_stats, move_host_to_another_cluster
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@attr(tier=2)
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    send_icmp.__name__,
    update_host_nics_stats.__name__
)
class TestCumulativeNetworkUsageHostStatisticsCase1(NetworkTest):
    """
    1) Check that sending ICMP traffic on the host increases its statistics.
    2) Move the host to another compatible cluster and check that statistics
        remains the same.
    """
    # General
    net_1 = rx_tx_conf.NETWORK_0
    ip_dict_1 = rx_tx_conf.BASIC_IP_DICT_NETMASK.get("host_1")
    ip_dict_2 = rx_tx_conf.BASIC_IP_DICT_NETMASK.get("host_2")
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "datacenter": dc,
            "cluster": conf.CL_0,
            "networks": rx_tx_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": ip_dict_1
            },
        },
        1: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": ip_dict_2
            },
        }
    }

    @polarion("RHEVM3-6654")
    def test_increase_traffic(self):
        """
        Increase total.rx and total.tx on the host by sending ICMP traffic
        from and to it
        Check the statistics increased on the host
        """
        assert helper.compare_nic_stats(
            nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
            total_rx=rx_tx_conf.TOTAL_RX, total_tx=rx_tx_conf.TOTAL_TX,
            oper=">"
        )

    @polarion("RHEVM3-6654")
    @pytest.mark.usefixtures(
        move_host_to_another_cluster.__name__
    )
    def test_move_same_ver_cluster(self):
        """
        Check statistics in a new Cluster are >= than in the original Cluster
        """
        testflow.step(
            "Move the host to another compatible cluster and check that "
            "statistics remains the same"
        )
        assert helper.compare_nic_stats(
            nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
            total_rx=rx_tx_conf.TOTAL_RX, total_tx=rx_tx_conf.TOTAL_TX
        )
