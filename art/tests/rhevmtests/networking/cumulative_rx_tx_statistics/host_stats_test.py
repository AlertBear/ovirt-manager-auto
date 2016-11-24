#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""

import time

import pytest

import config as rx_tx_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    host_prepare_setup, update_host_nics_stats, move_host_to_another_cluster
)


@attr(tier=2)
@pytest.mark.usefixtures(
    host_prepare_setup.__name__,
    update_host_nics_stats.__name__
)
class TestCumulativeNetworkUsageHostStatisticsCase1(NetworkTest):
    """
   Check that sending ICMP traffic on the host increases its statistics
    """
    __test__ = True

    @polarion("RHEVM3-6654")
    def test_increase_traffic(self):
        """
        Increase total.rx and total.tx on the host by sending ICMP traffic
        from and to it
        Check the statistics increased on the host
        """
        testflow.step("Increase rx/tx statistics on Host NICs by sending ICMP")
        helper.send_icmp(
            [
                (conf.VDS_1_HOST, rx_tx_conf.HOST_IPS[0]),
                (conf.VDS_0_HOST, rx_tx_conf.HOST_IPS[1])
            ]
        )
        time.sleep(20)
        assert helper.compare_nic_stats(
            nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
            total_rx=rx_tx_conf.TOTAL_RX, total_tx=rx_tx_conf.TOTAL_TX,
            oper=">"
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    host_prepare_setup.__name__,
    update_host_nics_stats.__name__,
    move_host_to_another_cluster.__name__
)
class TestCumulativeNetworkUsageHostStatisticsCase2(NetworkTest):
    """
   Move the host to another compatible cluster and check that statistics
   remains the same
    """
    __test__ = True

    @polarion("RHEVM3-6654")
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
