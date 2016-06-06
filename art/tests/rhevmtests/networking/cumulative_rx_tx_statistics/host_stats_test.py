#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""

import logging
import time

import pytest

import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import rx_tx_stat_host_case02, rx_tx_stat_host_setup_class

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(rx_tx_stat_host_setup_class.__name__)
class CumulativeNetworkUsageHostStatisticsCase1(NetworkTest):
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
                (conf.VDS_1_HOST, conf.HOST_IPS[0]),
                (conf.VDS_0_HOST, conf.HOST_IPS[1])
            ]
        )
        time.sleep(20)
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
                total_rx=conf.TOTAL_RX, total_tx=conf.TOTAL_TX, oper=">"
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(rx_tx_stat_host_case02.__name__)
class CumulativeNetworkUsageHostStatisticsCase2(NetworkTest):
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
        self.assertTrue(
            helper.compare_nic_stats(
                nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
                total_rx=conf.TOTAL_RX, total_tx=conf.TOTAL_TX
            )
        )
