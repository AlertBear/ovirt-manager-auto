#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for cumulative_rx_tx_statistics
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class CumulativeRxTxStatistics(NetworkFixtures):
    """
    cumulative_rx_tx_statistics
    """
    def __init__(self):
        super(CumulativeRxTxStatistics, self).__init__()
        self.ip_dict = conf.BASIC_IP_DICT_NETMASK

    def create_networks_on_setup(self, networks_dict):
        """
        Create networks on setup
        """
        assert hl_networks.createAndAttachNetworkSN(
            data_center=self.dc_0, cluster=self.cluster_0,
            network_dict=networks_dict
        )


class CumulativeRxTxStatisticsHost(CumulativeRxTxStatistics):
    """
    cumulative_rx_tx_statistics host
    """
    def __init__(self):
        super(CumulativeRxTxStatisticsHost, self).__init__()
        self.net_0 = conf.NETWORK_0
        self.stat_keys = conf.STAT_KEYS
        self.host_ips = None

    def generate_host_ips(self):
        """
        Generate host IPs
        """
        conf.HOST_IPS = network_helper.create_random_ips()
        self.host_ips = conf.HOST_IPS

    def host_create_networks_on_setup(self):
        """
        Create networks on setup
        """
        add_net_dict = {
            self.net_0: {
                "required": "false",
            }
        }
        self.create_networks_on_setup(networks_dict=add_net_dict)

    def attach_networks_on_hosts(self):
        """
        Attach networks on hosts
        """
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net_0,
                    "nic": None,
                    "ip": self.ip_dict,
                }
            }
        }
        for i in range(2):
            sn_dict["add"]["1"]["nic"] = conf.VDS_HOSTS[i].nics[1]
            self.ip_dict["ip_prefix"]["address"] = self.host_ips[i]
            assert hl_host_network.setup_networks(
                host_name=conf.HOSTS[i], **sn_dict
            )


class CumulativeRxTxStatisticsVm(CumulativeRxTxStatistics):
    """
    cumulative_rx_tx_statistics host
    """
    def __init__(self):
        super(CumulativeRxTxStatisticsVm, self).__init__()
        self.vm_nic_1 = conf.VM_NIC_1
        self.net_1 = conf.NETWORK_1
        self.net_2 = conf.NETWORK_2
        self.vm_ips = None

    def generate_vm_ips(self):
        """
        Generate host IPs
        """
        conf.VM_IPS = network_helper.create_random_ips()
        self.vm_ips = conf.VM_IPS

    def vm_create_networks_on_setup(self):
        """
        Create networks on setup
        """
        add_net_1_dict = {
            self.net_1: {
                "required": "false"
            },
            self.net_2: {
                "required": "false",
                "vlan_id": 2
            }
        }
        self.create_networks_on_setup(networks_dict=add_net_1_dict)

    def attach_networks_on_hosts(self):
        """
        Attach networks on hosts
        """
        sn_net_1_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": None
                },
                "2": {
                    "network": self.net_2,
                    "nic": None
                }
            }
        }

        for i in range(2):
            sn_net_1_dict["add"]["1"]["nic"] = conf.VDS_HOSTS[i].nics[1]
            sn_net_1_dict["add"]["2"]["nic"] = conf.VDS_HOSTS[i].nics[1]
            assert hl_host_network.setup_networks(
                host_name=conf.HOSTS[i], **sn_net_1_dict
            )

    def add_vnic_to_vms(self):
        """
        Add vNIC to VMs
        """
        for vm in [self.vm_0, self.vm_1]:
            assert ll_vms.addNic(
                positive=True, vm=vm, name=self.vm_nic_1,
                network=self.net_1, vnic_profile=self.net_1
            )

    def run_vms(self):
        """
        Run VMs
        """
        for host, vm in zip(
            [self.host_0_name, self.host_1_name], [self.vm_0, self.vm_1]
        ):
            assert network_helper.run_vm_once_specific_host(
                vm=vm, host=host, wait_for_up_status=True
            )

    def set_ips_on_vms_nic(self):
        """
        Configure IPs on VMs NIC
        """
        vms_and_ips = [
            (self.vm_0, self.vm_ips[0]),
            (self.vm_1, self.vm_ips[1])
        ]
        helper.config_ip(vms_and_ips)


@pytest.fixture(scope="module")
def rx_tx_stat_host_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    rx_tx_stat_host = CumulativeRxTxStatisticsHost()
    rx_tx_stat_host.generate_host_ips()

    def fin():
        """
        Finalizer for remove networks
        """
        network_helper.remove_networks_from_setup(
            hosts=conf.HOSTS[:2], dc=rx_tx_stat_host.dc_0
        )
    request.addfinalizer(fin)

    rx_tx_stat_host.host_create_networks_on_setup()
    rx_tx_stat_host.attach_networks_on_hosts()

    network_helper.send_icmp_sampler(
        host_resource=rx_tx_stat_host.vds_0_host,
        dst=rx_tx_stat_host.host_ips[1]
    )

    helper.send_icmp(
        [
            (rx_tx_stat_host.vds_0_host, rx_tx_stat_host.host_ips[0]),
            (rx_tx_stat_host.vds_1_host, rx_tx_stat_host.host_ips[1])
        ]
    )


@pytest.fixture(scope="class")
def rx_tx_stat_host_setup_class(request, rx_tx_stat_host_prepare_setup):
    """
    Setup for all CumulativeNetworkUsageHostStatistics classes
    """
    rx_tx_stat_host = CumulativeRxTxStatisticsHost()
    conf.NIC_STAT = hl_networks.get_nic_statistics(
        nic=rx_tx_stat_host.host_0_nics[1], host=rx_tx_stat_host.host_0_name,
        keys=rx_tx_stat_host.stat_keys
    )

    conf.TOTAL_RX = conf.NIC_STAT["data.total.rx"]
    conf.TOTAL_TX = conf.NIC_STAT["data.total.tx"]


@pytest.fixture(scope="class")
def rx_tx_stat_host_case02(request, rx_tx_stat_host_setup_class):
    """
    Fixture for CumulativeNetworkUsageHostStatisticsCase2
    """
    rx_tx_stat_host = CumulativeRxTxStatisticsHost()

    def fin():
        """
        Move host back to original cluster
        """
        hl_hosts.move_host_to_another_cluster(
            host=rx_tx_stat_host.host_0_name, cluster=rx_tx_stat_host.cluster_0
        )
    request.addfinalizer(fin)

    hl_hosts.move_host_to_another_cluster(
        host=rx_tx_stat_host.host_0_name, cluster=rx_tx_stat_host.cluster_1
    )


@pytest.fixture(scope="module")
def rx_tx_stat_vm_prepare_setup(request):
    """
    Prepare setup
    """
    rx_tx_stat_vm = CumulativeRxTxStatisticsVm()
    rx_tx_stat_vm.generate_vm_ips()

    def fin4():
        """
        Finalizer for remove networks from setup
        """
        network_helper.remove_networks_from_setup(
            hosts=conf.HOSTS[:2], dc=rx_tx_stat_vm.dc_0
        )
    request.addfinalizer(fin4)

    def fin3():
        """
        Finalizer for remove vNIC from VMs
        """
        for i in range(2):
            ll_vms.removeNic(True, conf.VM_NAME[i], rx_tx_stat_vm.vm_nic_1)
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for stop VMs
        """
        ll_vms.stopVms(conf.VM_NAME[:2])
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove ifcfg files
        """
        network_helper.remove_ifcfg_files(conf.VM_NAME[:2])
    request.addfinalizer(fin1)

    rx_tx_stat_vm.vm_create_networks_on_setup()
    rx_tx_stat_vm.attach_networks_on_hosts()
    rx_tx_stat_vm.add_vnic_to_vms()
    rx_tx_stat_vm.run_vms()
    rx_tx_stat_vm.set_ips_on_vms_nic()


@pytest.fixture(scope="class")
def rx_tx_stat_vm_case01(request, rx_tx_stat_vm_prepare_setup):
    """
    Fixture for CumulativeNetworkUsageStatisticsCase1
    """
    rx_tx_stat_vm = CumulativeRxTxStatisticsVm()
    conf.NIC_STAT = hl_networks.get_nic_statistics(
        nic=rx_tx_stat_vm.vm_nic_1, vm=rx_tx_stat_vm.vm_1, keys=conf.STAT_KEYS
    )
    err_msg = "Failed to get %s statistics on %s" % (
        rx_tx_stat_vm.vm_nic_1, rx_tx_stat_vm.vm_1
    )
    assert conf.NIC_STAT, err_msg

    vms_ips = [
        (helper.get_vm_resource(rx_tx_stat_vm.vm_0), conf.VM_IPS[0]),
        (helper.get_vm_resource(rx_tx_stat_vm.vm_1), conf.VM_IPS[1])
    ]

    network_helper.send_icmp_sampler(
        host_resource=vms_ips[0][0], dst=vms_ips[1][1]
    )
    while not all([int(conf.NIC_STAT[x]) > 1000 for x in conf.STAT_KEYS]):
        helper.send_icmp(vms_ips)
        conf.NIC_STAT = hl_networks.get_nic_statistics(
            nic=rx_tx_stat_vm.vm_nic_1, vm=rx_tx_stat_vm.vm_1,
            keys=conf.STAT_KEYS
        )
        assert conf.NIC_STAT, err_msg

    conf.TOTAL_RX = conf.NIC_STAT["data.total.rx"]
    conf.TOTAL_TX = conf.NIC_STAT["data.total.tx"]
