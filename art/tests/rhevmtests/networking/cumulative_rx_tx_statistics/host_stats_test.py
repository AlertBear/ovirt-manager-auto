#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""
import config as conf
import logging
from art.test_handler.tools import polarion  # pylint: disable=E0611
import helper
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.helper as net_helper
import time

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


@attr(tier=1)
class CumulativeHostStatisticsBase(TestCase):
    """
    Check Host statistics before the test
    Move host to another cluster if needed
    """
    move_host = True
    nic_stat = None
    total_rx = None
    total_tx = None

    @classmethod
    def setup_class(cls):
        """
        1. Get Host statistics
        2. Move host to another cluster if needed
        """
        logger.info(
            "Get %s statistics on %s", conf.HOST_4_NIC_1, conf.LAST_HOST
        )
        cls.nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_4_NIC_1, host=conf.LAST_HOST, keys=conf.STAT_KEYS
        )

        cls.total_rx = cls.nic_stat["data.total.rx"]
        cls.total_tx = cls.nic_stat["data.total.tx"]

        if cls.move_host:
            net_helper.move_host_to_another_cluster(
                host=conf.LAST_HOST, cluster=conf.CL_0
            )


class CumulativeNetworkUsageHostStatisticsCase1(CumulativeHostStatisticsBase):
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
        logger.info("Increase rx/tx statistics on Host NICs by sending ICMP")
        helper.send_icmp(
            [
                (conf.VDS_HOSTS[-2], conf.HOST_IPS[0]),
                (conf.VDS_HOSTS[-1], conf.HOST_IPS[1])
            ]
        )
        time.sleep(20)
        helper.compare_nic_stats(
            nic=conf.HOST_4_NIC_1, host=conf.LAST_HOST,
            total_rx=self.total_rx, total_tx=self.total_tx, oper=">"
        )


class CumulativeNetworkUsageHostStatisticsCase2(CumulativeHostStatisticsBase):
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
        helper.compare_nic_stats(
            nic=conf.HOST_4_NIC_1, host=conf.LAST_HOST,
            total_rx=self.total_rx, total_tx=self.total_tx
        )

    @classmethod
    def teardown_class(cls):
        """
        Return Host back to its original cluster
        """
        net_helper.move_host_to_another_cluster(
            host=conf.LAST_HOST, cluster=conf.CL_1
        )


class CumulativeNetworkUsageHostStatisticsCase3(CumulativeHostStatisticsBase):
    """
    1. Move the host to 3.5 version cluster and check that statistics
    are not available anymore
    2. Move the host back to the cluster with version >=3.6 and make sure the
    statistics are zero
    """
    __test__ = True
    move_host = False

    @classmethod
    def setup_class(cls):
        """
        1. Create a DC/Cluster with 3.5 version
        2. Attach a network to the new DC/Cluster
        """
        add_net_dict = {conf.NET_0: {"required": "false"}}
        super(CumulativeNetworkUsageHostStatisticsCase3, cls).setup_class()

        if not hl_networks.create_basic_setup(
            datacenter=conf.DC_3_5, cpu=conf.CPU_NAME,
            storage_type=conf.STORAGE_TYPE,
            version=conf.VERSION[5], cluster=conf.CL_3_5
        ):
            raise conf.NET_EXCEPTION("Failed to create 3.5 setup")

        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_3_5, cluster=conf.CL_3_5,
            network_dict=add_net_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create and attach %s to DC/Cluster" % conf.NET_0
            )

    @polarion("RHEVM3-6683")
    def test_01_move_host_cluster_3_5(self):
        """
        1. Move host to 3.5 ver cluster
        2. Check statistics in a new Cluster are N/A
        """
        net_helper.move_host_to_another_cluster(
            host=conf.LAST_HOST, cluster=conf.CL_3_5
        )
        time.sleep(20)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_4_NIC_1, host=conf.LAST_HOST,
            keys=conf.STAT_KEYS
        )

        logger.info(
            "Check statistics are N/A on Host that resides on 3.5 Cluster"
        )
        if (
            nic_stat["data.total.rx"] is not None or
            nic_stat["data.total.tx"] is not None
        ):
            raise conf.NET_EXCEPTION(
                "Host statistics should be N/A and they are not"
            )

    @polarion("RHEVM3-9603")
    def test_02_move_host_comp_ver_cluster(self):
        """
        1. Move host back to its original cluster
        2. Check statistics in the original Cluster are zero
        """
        net_helper.move_host_to_another_cluster(
            host=conf.LAST_HOST, cluster=conf.CL_1
        )

        logger.info(
            "Check statistics are zero on Host that moved back"
            " from 3.5 Cluster"
        )
        time.sleep(15)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_4_NIC_1, host=conf.LAST_HOST, keys=conf.STAT_KEYS
        )
        if nic_stat["data.total.tx"] != 0.0:
            raise conf.NET_EXCEPTION(
                "Host statistics should be zero and they are not"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the 3.5 DC/Cluster created for the tests
        """
        if not hl_networks.remove_basic_setup(
            datacenter=conf.DC_3_5, cluster=conf.CL_3_5
        ):
            logger.error("Couldn't remove 3.5 DC/Cluster from the setup")
