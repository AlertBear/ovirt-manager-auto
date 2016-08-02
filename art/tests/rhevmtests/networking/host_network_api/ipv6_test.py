#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
IPv6 tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as conf
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    clean_host_interfaces, ipv6_prepare_setup
)


@attr(tier=2)
@pytest.mark.usefixtures(
    ipv6_prepare_setup.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApiIpV601(NetworkTest):
    """
    Attach network with static IPv6 over bridge
    """
    __test__ = True
    ip_v6_1 = conf.IPV6_IPS[1]
    ip_v6_2 = conf.IPV6_IPS[2]
    ip_v6_3 = conf.IPV6_IPS[3]
    ip_v6_4 = conf.IPV6_IPS[4]
    ip_v6_5 = conf.IPV6_IPS[5]
    ip_v6_6 = conf.IPV6_IPS[6]
    net_1 = conf.IPV6_NETS[1][0]
    net_2 = conf.IPV6_NETS[1][1]
    net_3 = conf.IPV6_NETS[1][2]
    net_4 = conf.IPV6_NETS[1][3]
    net_5 = conf.IPV6_NETS[1][4]
    net_6 = conf.IPV6_NETS[1][5]
    dummy_1 = net_conf.DUMMYS[0]
    dummy_2 = net_conf.DUMMYS[1]
    dummy_3 = net_conf.DUMMYS[2]
    dummy_4 = net_conf.DUMMYS[3]
    dummy_5 = net_conf.DUMMYS[4]
    dummy_6 = net_conf.DUMMYS[5]
    vlan_bond_dummies = net_conf.DUMMYS[6:8]
    bond_dummies = net_conf.DUMMYS[8:10]
    host_index = 0

    @polarion("RHEVM3-16627")
    def test_static_ipv6_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over bridge
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_1
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": self.dummy_1,
                    "ip": conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over bridge"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16639")
    def test_static_ipv6_vlan_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN bridge
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_2
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": self.dummy_2,
                    "ip": conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over VLAN bridge"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16640")
    def test_static_ipv6_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over BOND bridge
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_3
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_3,
                    "nic": "bond10",
                    "ip": conf.BASIC_IPV6_DICT,
                    "slaves": self.bond_dummies
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over BOND bridge"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16641")
    def test_static_ipv6_vlan_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN BOND bridge
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_4
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": "bond10",
                    "ip": conf.BASIC_IPV6_DICT,
                    "slaves": self.vlan_bond_dummies
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over VLAN BOND bridge"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16642")
    def test_static_ipv6_non_vm_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_5
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_5,
                    "nic": self.dummy_5,
                    "ip": conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over Non-VM"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-16643")
    def test_static_ipv6_non_vm_vlan_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM VLAN
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_6
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_6,
                    "nic": self.dummy_6,
                    "ip": conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network with static IPv6 over Non-VM VLAN"
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )
