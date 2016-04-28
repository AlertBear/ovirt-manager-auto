#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""

import logging
import time

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import helper
import pytest
import rhevmtests.networking.config as conf
from _pytest_art.marks import tier2
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    rx_tx_stat_host_case02, rx_tx_stat_host_case03,
    rx_tx_stat_host_setup_class
)

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(rx_tx_stat_host_setup_class.__name__)
class CumulativeNetworkUsageHostStatisticsCase1(NetworkTest):
    """
   Check that sending ICMP traffic on the host increases its statistics
    """
    __test__ = True
    move_host = False

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


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(rx_tx_stat_host_case02.__name__)
class CumulativeNetworkUsageHostStatisticsCase2(NetworkTest):
    """
   Move the host to another compatible cluster and check that statistics
   remains the same
    """
    __test__ = True
    move_host = True

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


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(rx_tx_stat_host_case03.__name__)
class CumulativeNetworkUsageHostStatisticsCase3(NetworkTest):
    """
    1. Move the host to 3.5 version cluster and check that statistics
    are not available anymore
    2. Move the host back to the cluster with version >=3.6 and make sure the
    statistics are zero
    """
    __test__ = True
    move_host = False

    @polarion("RHEVM3-6683")
    def test_01_move_host_cluster_3_5(self):
        """
        1. Move host to 3.5 ver cluster
        2. Check statistics in a new Cluster are N/A
        """
        testflow.step("Move host to 3.5 ver cluster")
        self.assertTrue(
            hl_hosts.move_host_to_another_cluster(
                host=conf.HOST_0_NAME, cluster=conf.CL_3_5
            )
        )
        time.sleep(20)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME,
            keys=conf.STAT_KEYS
        )

        testflow.step(
            "Check statistics are N/A on Host that resides on 3.5 Cluster"
        )
        self.assertIsNone(nic_stat["data.total.rx"])
        self.assertIsNone(nic_stat["data.total.tx"])

    @polarion("RHEVM3-9603")
    def test_02_move_host_comp_ver_cluster(self):
        """
        1. Move host back to its original cluster
        2. Check statistics in the original Cluster are zero
        """
        testflow.step("Move host back to its original cluster")
        self.assertTrue(
            hl_hosts.move_host_to_another_cluster(
                host=conf.HOST_0_NAME, cluster=conf.CL_0
            )
        )
        testflow.step(
            "Check statistics are zero on Host that moved back from 3.5 "
            "Cluster"
        )
        time.sleep(15)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_0_NICS[1], host=conf.HOST_0_NAME, keys=conf.STAT_KEYS
        )
        self.assertEqual(
            nic_stat["data.total.tx"], 0.0,
            "Host statistics should be zero and they are not"
        )
