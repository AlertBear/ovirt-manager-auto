#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics for VM
"""

import config as conf
import logging
import helper
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.helper as net_help


logger = logging.getLogger("Cumulative_RX_TX_Statistics_Cases")


@attr(tier=1)
class CumulativeNetworkUsageStatisticsCase1(TestCase):
    """
    Add vNIC to VM and start VM
    Hot unplug the vNIC
    Hot plug the vNIC
    Change the vNIC profile to conf.NET_0
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
            conf.NET_1: {
                "required": "false"
            }
        }
        sn_net_1_dict = {
            "add": {
                "1": {
                    "network": conf.NET_1,
                    "nic": conf.VDS_HOSTS[-1].nics[2]
                }
            }
        }

        logger.info("Create and attach %s to DC/Cluster", conf.NET_1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CLUSTER_NAME[1],
            network_dict=add_net_1_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create and attach %s to DC/Cluster" % conf.NET_1
            )
        logger.info("Attaching %s to %s via SN", conf.NET_1, conf.LAST_HOST)
        if not hl_host_network.setup_networks(
            host_name=conf.LAST_HOST, **sn_net_1_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" %
                (conf.NET_1, conf.LAST_HOST)
            )

        for i in range(-2, 0):
            logger.info("Adding %s to %s", conf.NIC_1, conf.VM_NAME[i])
            if not ll_vms.addNic(
                positive=True, vm=conf.VM_NAME[i], name=conf.NIC_1,
                network=conf.NET_0, vnic_profile=conf.NET_0
            ):
                raise conf.NET_EXCEPTION(
                    "Failed to add %s to %s" % (conf.NIC_1, conf.VM_NAME[i])
                )
            logger.info(
                "Starting VM %s on host %s", conf.VM_NAME[i], conf.HOSTS[i+4]
            )
            if not net_help.run_vm_once_specific_host(
                vm=conf.VM_NAME[i], host=conf.HOSTS[i+4], wait_for_ip=True
            ):
                raise conf.NET_EXCEPTION(
                    "Cannot start VM %s on host %s" %
                    (conf.VM_NAME[i], conf.HOSTS[i+4])
                )
        vms_and_ips = [
            (conf.VM_ON_CL1, conf.VM_IPS[0]),
            (conf.VM_ON_CL2, conf.VM_IPS[1])
        ]
        helper.config_ip(vms_and_ips)

        logger.info("Get %s statistics on %s", conf.NIC_1, conf.VM_ON_CL2)
        cls.nic_stat = hl_networks.get_nic_statistics(
            nic=conf.NIC_1, vm=conf.VM_ON_CL2, keys=conf.STAT_KEYS
        )
        if not cls.nic_stat:
            raise conf.NET_EXCEPTION(
                "Failed to get %s statistics on %s" %
                (conf.NIC_1, conf.VM_ON_CL2)
            )
        vms_ips = [
            (helper.get_vm_resource(conf.VM_ON_CL1), conf.VM_IPS[0]),
            (helper.get_vm_resource(conf.VM_ON_CL2), conf.VM_IPS[1])
        ]
        while not all([int(cls.nic_stat[x]) > 1000 for x in conf.STAT_KEYS]):
            helper.send_icmp(vms_ips)
            logger.info(
                "Get %s statistics on %s", conf.NIC_1, conf.VM_ON_CL2
            )
            cls.nic_stat = hl_networks.get_nic_statistics(
                nic=conf.NIC_1, vm=conf.VM_ON_CL2, keys=conf.STAT_KEYS
            )
            if not cls.nic_stat:
                raise conf.NET_EXCEPTION(
                    "Failed to get %s statistics on %s" %
                    (conf.NIC_1, conf.VM_ON_CL2)
                )
        cls.total_rx = cls.nic_stat["data.total.rx"]
        cls.total_tx = cls.nic_stat["data.total.tx"]

    @polarion("RHEVM3-6639")
    def test_01_hot_unplug_vnic(self):
        """
        Hot unplug the vNIC
        """
        helper.plug_unplug_vnic(conf.VM_ON_CL2, False)
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_ON_CL2, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    def test_02_hot_plug_vnic(self):
        """
        Hot plug the vNIC
        """
        helper.plug_unplug_vnic(conf.VM_ON_CL2)
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_ON_CL2, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    def test_03_change_vnic_profile(self):
        """
        Change the vNIC network to conf.NET_0
        """
        profile_dict = {
            "network": conf.NET_1
        }
        logger.info("Change %s profile to %s", conf.NIC_1, conf.NET_1)
        if not ll_vms.updateNic(
            True, conf.VM_ON_CL2, conf.NIC_1, **profile_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to change %s profile to %s" % (conf.NIC_1, conf.NET_1)
            )
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_ON_CL2, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    def test_04_change_vnic_to_empty_network(self):
        """
        Attach the vNIC to <empty network>
        """
        profile_dict = {
            "network": None
        }
        logger.info("Change %s to empty profile", conf.NIC_1)
        if not ll_vms.updateNic(
            True, conf.VM_ON_CL2, conf.NIC_1, **profile_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to change %s to empty profile" % conf.NIC_1
            )
        helper.compare_nic_stats(
            nic=conf.NIC_1, vm=conf.VM_ON_CL2, total_rx=self.total_rx,
            total_tx=self.total_tx
        )

    @classmethod
    def teardown_class(cls):
        """
        Unplug NICs from VMs
        Remove NICs from VMs
        """
        for i in range(-2, 0):
            helper.plug_unplug_vnic(conf.VM_NAME[i], False)
            logger.info("Removing %s from %s", conf.NIC_1, conf.VM_NAME[i])
            if not ll_vms.removeNic(True, conf.VM_NAME[i], conf.NIC_1):
                logger.error(
                    "Failed to remove %s from %s", conf.NIC_1, conf.VM_NAME[i]
                )
                cls.test_failed = True
        cls.teardown_exception()
