#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for Host
"""

import time
import helper
import logging
import config as conf
from art import unittest_lib
from art.core_api import apis_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


def setup_module():
    """
    Create and attach networks on DC/Cluster and hosts
    Increase rx/tx statistics on Host NICs by sending ICMP
    """
    add_net_dict = {
        conf.HOST_NET: {
            "required": "false",
        }
    }
    sn_dict = {
        "add": {
            "1": {
                "network": conf.HOST_NET,
                "nic": None,
                "ip": conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    logger.info("Create and attach %s to DC/Clusters", conf.HOST_NET)
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_0, cluster=conf.CL_0, network_dict=add_net_dict
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create and attach %s to DC/Cluster" % conf.HOST_NET
        )
    for i in range(2):
        logger.info(
            "Attaching %s to %s via SN", conf.HOST_NET, conf.HOSTS[i]
        )
        sn_dict["add"]["1"]["nic"] = conf.VDS_HOSTS[i].nics[1]
        conf.BASIC_IP_DICT_NETMASK["ip_prefix"]["address"] = conf.HOST_IPS[i]
        if not hl_host_network.setup_networks(
            host_name=conf.HOSTS[i], **sn_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" %
                (conf.HOST_NET, conf.HOSTS[i])
            )

    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=hl_networks.checkICMPConnectivity,
        host=conf.VDS_HOSTS[0].ip, user=conf.HOSTS_USER,
        password=conf.HOSTS_PW, ip=conf.HOST_IPS[1]
    )
    if not sample.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION("Couldn't ping %s " % conf .HOST_IPS[1])

    logger.info("Increase rx/tx statistics on Host NICs by sending ICMP")
    helper.send_icmp([
        (conf.VDS_HOSTS[1], conf.HOST_IPS[0]),
        (conf.VDS_HOSTS[0], conf.HOST_IPS[1])
    ])


def teardown_module():
    """
    Remove all network from setup
    """
    network_helper.remove_networks_from_setup(
        hosts=conf.HOSTS[:2], dc=conf.DC_0
    )


@unittest_lib.attr(tier=2)
class CumulativeHostStatisticsBase(unittest_lib.NetworkTest):
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
            "Get %s statistics on %s", conf.HOST_0_NIC_1, conf.HOST_0_NAME
        )
        cls.nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_0_NIC_1, host=conf.HOST_0_NAME, keys=conf.STAT_KEYS
        )

        cls.total_rx = cls.nic_stat["data.total.rx"]
        cls.total_tx = cls.nic_stat["data.total.tx"]

        if cls.move_host:
            hl_hosts.move_host_to_another_cluster(
                host=conf.HOST_0_NAME, cluster=conf.CL_0
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
                (conf.VDS_HOSTS[1], conf.HOST_IPS[0]),
                (conf.VDS_HOSTS[0], conf.HOST_IPS[1])
            ]
        )
        time.sleep(20)
        helper.compare_nic_stats(
            nic=conf.HOST_0_NIC_1, host=conf.HOST_0_NAME,
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
            nic=conf.HOST_0_NIC_1, host=conf.HOST_0_NAME,
            total_rx=self.total_rx, total_tx=self.total_tx
        )

    @classmethod
    def teardown_class(cls):
        """
        Return Host back to its original cluster
        """
        hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_0_NAME, cluster=conf.CL_0
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
        add_net_dict = {
            conf.HOST_NET: {
                "required": "false"
            }
        }
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
                "Failed to create and attach %s to DC/Cluster" % conf.HOST_NET
            )

    @polarion("RHEVM3-6683")
    def test_01_move_host_cluster_3_5(self):
        """
        1. Move host to 3.5 ver cluster
        2. Check statistics in a new Cluster are N/A
        """
        hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_0_NAME, cluster=conf.CL_3_5
        )
        time.sleep(20)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_0_NIC_1, host=conf.HOST_0_NAME,
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
        hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_0_NAME, cluster=conf.CL_0
        )

        logger.info(
            "Check statistics are zero on Host that moved back"
            " from 3.5 Cluster"
        )
        time.sleep(15)
        nic_stat = hl_networks.get_nic_statistics(
            nic=conf.HOST_0_NIC_1, host=conf.HOST_0_NAME, keys=conf.STAT_KEYS
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
