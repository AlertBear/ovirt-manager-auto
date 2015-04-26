#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics
"""

import config as c
import logging
import helper
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


# @polarion(id="RHEVM3-6639")
@attr(tier=1)
class CumulativeNetworkUsageStatisticsCase1(TestCase):
    """
    Add vNIC to VM and start VM
    Hot unplug the vNIC
    Hot plug the vNIC
    Change the vNIC profile to c.NET_1
    Change the vNIC profile to <empty network>
    """
    __test__ = True

    nic_stat = None
    total_rx = None
    total_tx = None

    @classmethod
    def setup_class(cls):
        """
        1. Add vNIC to two VMs and start VM
        2. Configure temp IP on the VMs
        3. Wait till vNICs stats are above 1000
        """
        add_net_1_dict = {
            c.NET_1: {
                "required": "false"
            }
        }
        sn_net_1_dict = {
            "add": {
                "1": {
                    "network": c.NET_1,
                    "nic": c.VDS_HOSTS[0].nics[2]
                }
            }
        }
        logger.info("Create and attach %s to DC/Cluster", c.NET_1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CLUSTER_NAME[0],
            network_dict=add_net_1_dict
        ):
            raise helper.c.NET_EXCEPTION(
                "Failed to create and attach %s to DC/Cluster" % c.NET_1
            )
        logger.info("Attaching %s to %s via SN", c.NET_1, c.HOSTS[0])
        if not hl_host_network.setup_networks(
            host_name=c.HOSTS[0], **sn_net_1_dict
        ):
            raise helper.c.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" % (c.NET_1, c.HOSTS[0])
            )

        for i in range(2):
            logger.info("Adding %s to %s", c.NIC_1, c.VM_NAME[i])
            if not ll_vms.addNic(
                positive=True, vm=c.VM_NAME[i], name=c.NIC_1,
                network=c.NET_0, vnic_profile=c.NET_0
            ):
                raise helper.c.NET_EXCEPTION(
                    "Failed to add %s to %s" % (c.NIC_1, c.VM_NAME[i])
                )
            logger.info("Starting VM %s on host %s", c.VM_NAME[i], c.HOSTS[i])
            if not hl_vms.start_vm_on_specific_host(
                vm=c.VM_NAME[i], host=c.HOSTS[i]
            ):
                raise helper.c.NET_EXCEPTION(
                    "Cannot start VM %s on host %s" %
                    (c.VM_NAME[i], c.HOSTS[i])
                )
        vms_and_ips = [(c.VM_NAME[0], c.IPS[0]), (c.VM_NAME[1], c.IPS[1])]
        helper.config_temp_ip(vms_and_ips)

        logger.info("Get %s statistics on %s", c.NIC_1, c.VM_NAME[0])
        cls.nic_stat = hl_networks.get_nic_statistics(
            nic=c.NIC_1, vm=c.VM_NAME[0], keys=c.STAT_KEYS
        )
        if not cls.nic_stat:
            raise helper.c.NET_EXCEPTION(
                "Failed to get %s statistics on %s" % (c.NIC_1, c.VM_NAME[0])
            )
        vms_ips = [(c.VM_NAME[0], c.IPS[0]), (c.VM_NAME[1], c.IPS[1])]
        while not all([int(cls.nic_stat[x]) > 1000 for x in c.STAT_KEYS]):
            helper.ping_from_to_vms(vms_ips)
            logger.info("Get %s statistics on %s", c.NIC_1, c.VM_NAME[0])
            cls.nic_stat = hl_networks.get_nic_statistics(
                nic=c.NIC_1, vm=c.VM_NAME[0], keys=c.STAT_KEYS
            )
            if not cls.nic_stat:
                raise helper.c.NET_EXCEPTION(
                    "Failed to get %s statistics on %s" %
                    (c.NIC_1, c.VM_NAME[0])
                )
        cls.total_rx = cls.nic_stat["data.total.rx"]
        cls.total_tx = cls.nic_stat["data.total.tx"]

    def test_01_hot_unplug_vnic(self):
        """
        Hot unplug the vNIC
        """
        helper.plug_unplug_vnic(c.VM_NAME[0], False)
        helper.check_if_nic_stat_reset(
            c.NIC_1, c.VM_NAME[0], self.total_rx, self.total_tx
        )

    def test_02_hot_plug_vnic(self):
        """
        Hot plug the vNIC
        """
        helper.plug_unplug_vnic(c.VM_NAME[0])
        helper.check_if_nic_stat_reset(
            c.NIC_1, c.VM_NAME[0], self.total_rx, self.total_tx
        )

    def test_03_change_vnic_profile(self):
        """
        Change the vNIC network to c.NET_1
        """
        profile_dict = {
            "network": c.NET_1
        }
        logger.info("Change %s profile to %s", c.NIC_1, c.NET_1)
        if not ll_vms.updateNic(True, c.VM_NAME[0], c.NIC_1, **profile_dict):
            raise c.NET_EXCEPTION(
                "Failed to change %s profile to %s" % (c.NIC_1, c.NET_1)
            )
        helper.check_if_nic_stat_reset(
            c.NIC_1, c.VM_NAME[0], self.total_rx, self.total_tx
        )

    def test_04_change_vnic_to_empty_network(self):
        """
        Attach the vNIC to <empty network>
        """
        profile_dict = {
            "network": None
        }
        logger.info("Change %s to empty profile", c.NIC_1)
        if not ll_vms.updateNic(True, c.VM_NAME[0], c.NIC_1, **profile_dict):
            raise c.NET_EXCEPTION(
                "Failed to change %s network to %s" % (c.NIC_1, c.NET_1)
            )
        helper.check_if_nic_stat_reset(
            c.NIC_1, c.VM_NAME[0], self.total_rx, self.total_tx
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        for i in range(2):
            helper.plug_unplug_vnic(c.VM_NAME[i], False)
            logger.info("Removing %s from %s", c.NIC_1, c.VM_NAME[i])
            if not ll_vms.removeNic(True, c.VM_NAME[i], c.NIC_1):
                logger.error(
                    "Failed to remove %s from %s", c.NIC_1, c.VM_NAME[i]
                )
                cls.test_failed = True
        cls.teardown_exception()
