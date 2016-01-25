#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for VM
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.core_api import apis_exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network


logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


def setup_module():
    """
    Create and attach network on DC/Cluster and host
    Add vNIC to VMs
    Start VMs
    Configure IPs on the VMs
    """
    add_net_1_dict = {
        conf.VM_NET: {
            "required": "false"
        },
        conf.EXTRA_NET: {
            "required": "false",
            "vlan_id": 2
        }
    }
    sn_net_1_dict = {
        "add": {
            "1": {
                "network": conf.VM_NET,
                "nic": None
            },
            "2": {
                "network": conf.EXTRA_NET,
                "nic": None
            }
        }
    }

    logger.info("Create and attach %s to DC/Cluster", conf.VM_NET)
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_0, cluster=conf.CL_0, network_dict=add_net_1_dict
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create and attach %s to DC/Cluster" % conf.VM_NET
        )
    for i in range(2):
        logger.info(
            "Attaching %s to %s and %s via SN",
            conf.VM_NET, conf.EXTRA_NET, conf.HOSTS[i]
        )
        sn_net_1_dict["add"]["1"]["nic"] = conf.VDS_HOSTS[i].nics[1]
        sn_net_1_dict["add"]["2"]["nic"] = conf.VDS_HOSTS[i].nics[1]
        if not hl_host_network.setup_networks(
            host_name=conf.HOSTS[i], **sn_net_1_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" %
                (conf.VM_NET, conf.HOSTS[i])
            )

    for i in range(2):
        logger.info("Adding %s to %s", conf.NIC_1, conf.VM_NAME[i])
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_NAME[i], name=conf.NIC_1,
            network=conf.VM_NET, vnic_profile=conf.VM_NET
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add %s to %s" % (conf.NIC_1, conf.VM_NAME[i])
            )
        logger.info(
            "Starting VM %s on host %s", conf.VM_NAME[i], conf.HOSTS[i]
        )
        if not network_helper.run_vm_once_specific_host(
            vm=conf.VM_NAME[i], host=conf.HOSTS[i], wait_for_ip=True
        ):
            raise conf.NET_EXCEPTION(
                "Cannot start VM %s on host %s" %
                (conf.VM_NAME[i], conf.HOSTS[i])
            )
    vms_and_ips = [
        (conf.VM_0, conf.VM_IPS[0]),
        (conf.VM_1, conf.VM_IPS[1])
    ]
    helper.config_ip(vms_and_ips)


def teardown_module():
    """
    Stop VMs
    Remove NICs from VMs
    Remove all network from setup
    """
    network_helper.remove_ifcfg_files(conf.VM_NAME[:2])
    logger.info("Stopping VMS: %s", conf.VM_NAME[:2])
    if not ll_vms.stopVms(conf.VM_NAME[:2]):
        logger.error("Failed to stop VMS: %s", conf.VM_NAME[:2])

    for i in range(2):
        err = "Failed to remove %s from %s" % (conf.NIC_1, conf.VM_NAME[i])
        logger.info("Removing %s from %s", conf.NIC_1, conf.VM_NAME[i])
        try:
            if not ll_vms.removeNic(True, conf.VM_NAME[i], conf.NIC_1):
                logger.error(err)
        except apis_exceptions.EntityNotFound:
            logger.error(err)

    network_helper.remove_networks_from_setup(
        hosts=conf.HOSTS[:2], dc=conf.DC_0
    )


@unittest_lib.attr(tier=2)
class CumulativeNetworkUsageStatisticsCase1(unittest_lib.NetworkTest):
    """
    Hot unplug the vNIC
    Hot plug the vNIC
    Change the vNIC profile to conf.EXTRA_NET
    Change the vNIC profile to <empty network>
    """
    __test__ = True

    nic_stat = None
    total_rx = None
    total_tx = None

    @classmethod
    def setup_class(cls):
        """
        Wait till vNICs stats are above 1000
        """
        logger.info("Get %s statistics on %s", conf.NIC_1, conf.VM_1)
        cls.nic_stat = hl_networks.get_nic_statistics(
            nic=conf.NIC_1, vm=conf.VM_1, keys=conf.STAT_KEYS
        )
        if not cls.nic_stat:
            raise conf.NET_EXCEPTION(
                "Failed to get %s statistics on %s" %
                (conf.NIC_1, conf.VM_1)
            )
        vms_ips = [
            (helper.get_vm_resource(conf.VM_0), conf.VM_IPS[0]),
            (helper.get_vm_resource(conf.VM_1), conf.VM_IPS[1])
        ]

        network_helper.send_icmp_sampler(
            host_resource=vms_ips[0][0], dst=vms_ips[1][1]
        )
        while not all([int(cls.nic_stat[x]) > 1000 for x in conf.STAT_KEYS]):
            helper.send_icmp(vms_ips)
            logger.info(
                "Get %s statistics on %s", conf.NIC_1, conf.VM_1
            )
            cls.nic_stat = hl_networks.get_nic_statistics(
                nic=conf.NIC_1, vm=conf.VM_1, keys=conf.STAT_KEYS
            )
            if not cls.nic_stat:
                raise conf.NET_EXCEPTION(
                    "Failed to get %s statistics on %s" %
                    (conf.NIC_1, conf.VM_1)
                )
        cls.total_rx = cls.nic_stat["data.total.rx"]
        cls.total_tx = cls.nic_stat["data.total.tx"]

    @polarion("RHEVM3-13580")
    def test_01_change_vnic_profile(self):
        """
        Change the vNIC network to conf.EXTRA_NET
        """
        profile_dict = {
            "network": conf.EXTRA_NET
        }
        logger.info("Change %s profile to %s", conf.NIC_1, conf.EXTRA_NET)
        if not ll_vms.updateNic(
            True, conf.VM_1, conf.NIC_1, **profile_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to change %s profile to %s" %
                (conf.NIC_1, conf.EXTRA_NET)
            )
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_1, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    @polarion("RHEVM3-13581")
    def test_02_change_vnic_to_empty_network(self):
        """
        Attach the vNIC to <empty network>
        """
        profile_dict = {
            "network": None
        }
        logger.info("Change %s to empty profile", conf.NIC_1)
        if not ll_vms.updateNic(
            True, conf.VM_1, conf.NIC_1, **profile_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to change %s to empty profile" % conf.NIC_1
            )
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_1, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    @polarion("RHEVM3-6639")
    def test_03_hot_unplug_vnic(self):
        """
        Hot unplug the vNIC
        """
        helper.plug_unplug_vnic(conf.VM_1, False)
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_1, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    @polarion("RHEVM3-13512")
    def test_04_hot_plug_vnic(self):
        """
        Hot plug the vNIC
        """
        helper.plug_unplug_vnic(conf.VM_1)
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_1, total_rx=self.total_rx,
            total_tx=self.total_tx
        )
