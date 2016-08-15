#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
IPv6 tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from rhevmtests.networking import helper as network_helper
from art.unittest_lib import attr, NetworkTest, testflow
from rhevmtests.networking.fixtures import (
    clean_host_interfaces, NetworkFixtures
)


@pytest.fixture(scope="module", autouse=True)
def ipv6_prepare_setup(request):
    """
    Prepare setup for ipv6 tests
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=net_api_conf.IPV6_NETS_DICT, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__
)
class TestHostNetworkApiIpV601(NetworkTest):
    """
    Attach network with static IPv6 over bridge
    """
    __test__ = True
    ip_v6_1 = net_api_conf.IPV6_IPS[1]
    ip_v6_2 = net_api_conf.IPV6_IPS[2]
    ip_v6_3 = net_api_conf.IPV6_IPS[3]
    ip_v6_4 = net_api_conf.IPV6_IPS[4]
    ip_v6_5 = net_api_conf.IPV6_IPS[5]
    ip_v6_6 = net_api_conf.IPV6_IPS[6]
    net_1 = net_api_conf.IPV6_NETS[1][0]
    net_2 = net_api_conf.IPV6_NETS[1][1]
    net_3 = net_api_conf.IPV6_NETS[1][2]
    net_4 = net_api_conf.IPV6_NETS[1][3]
    net_5 = net_api_conf.IPV6_NETS[1][4]
    net_6 = net_api_conf.IPV6_NETS[1][5]
    dummy_1 = conf.DUMMYS[0]
    dummy_2 = conf.DUMMYS[1]
    dummy_3 = conf.DUMMYS[2]
    dummy_4 = conf.DUMMYS[3]
    dummy_5 = conf.DUMMYS[4]
    dummy_6 = conf.DUMMYS[5]
    vlan_bond_dummies = conf.DUMMYS[6:8]
    bond_dummies = conf.DUMMYS[8:10]
    bond_1 = "bond10"
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-16627")
    def test_static_ipv6_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over bridge
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_1
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": self.dummy_1,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over bridge %s",
            self.net_1, net_api_conf.BASIC_IPV6_DICT, self.dummy_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16639")
    def test_static_ipv6_vlan_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN bridge
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_2
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": self.dummy_2,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over VLAN bridge",
            self.net_2, net_api_conf.BASIC_IPV6_DICT
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16640")
    def test_static_ipv6_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over BOND bridge
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_3
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_3,
                    "nic": self.bond_1,
                    "ip": net_api_conf.BASIC_IPV6_DICT,
                    "slaves": self.bond_dummies
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over BOND bridge %s",
            self.net_3, net_api_conf.BASIC_IPV6_DICT, self.bond_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16641")
    def test_static_ipv6_vlan_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN BOND bridge
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_4
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": self.bond_1,
                    "ip": net_api_conf.BASIC_IPV6_DICT,
                    "slaves": self.vlan_bond_dummies
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over VLAN BOND bridge %s",
            self.net_4, net_api_conf.BASIC_IPV6_DICT, self.bond_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16642")
    def test_static_ipv6_non_vm_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_5
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_5,
                    "nic": self.dummy_5,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over Non-VM",
            self.net_5, net_api_conf.BASIC_IPV6_DICT

        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16643")
    def test_static_ipv6_non_vm_vlan_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM VLAN
        """
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_6
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_6,
                    "nic": self.dummy_6,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over Non-VM VLAN",
            self.net_6, net_api_conf.BASIC_IPV6_DICT
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
