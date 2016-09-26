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
@pytest.mark.incremental
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
    ip_v6_7 = net_api_conf.IPV6_IPS[7]
    ip_v6_8 = net_api_conf.IPV6_IPS[8]
    ip_v6_9 = net_api_conf.IPV6_IPS[9]
    ip_v4_7 = net_api_conf.IPV4_IPS[7]
    net_1 = net_api_conf.IPV6_NETS[1][0]
    net_2 = net_api_conf.IPV6_NETS[1][1]
    net_3 = net_api_conf.IPV6_NETS[1][2]
    net_4 = net_api_conf.IPV6_NETS[1][3]
    net_5 = net_api_conf.IPV6_NETS[1][4]
    net_6 = net_api_conf.IPV6_NETS[1][5]
    bond_1 = "bond10"
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM-16627")
    def test_01_static_ipv6_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over bridge
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_1
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv6 %s over bridge %s",
            self.net_1, net_api_conf.BASIC_IPV6_DICT, dummy_nic
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM-16639")
    def test_02_static_ipv6_vlan_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN bridge
        """
        dummy_nic = conf.HOST_0_NICS[-2]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_2
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": dummy_nic,
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

    @polarion("RHEVM-16640")
    def test_03_static_ipv6_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over BOND bridge
        """
        bond_dummies = conf.HOST_0_NICS[-5:-3]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_3
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_3,
                    "nic": self.bond_1,
                    "ip": net_api_conf.BASIC_IPV6_DICT,
                    "slaves": bond_dummies
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

    @polarion("RHEVM-16641")
    def test_04_static_ipv6_vlan_bond_bridge_network_on_host(self):
        """
        Attach network with static IPv6 over VLAN BOND bridge
        """
        bond_dummies = conf.HOST_0_NICS[-7:-5]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_4
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": self.bond_1,
                    "ip": net_api_conf.BASIC_IPV6_DICT,
                    "slaves": bond_dummies
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

    @polarion("RHEVM-16642")
    def test_05_static_ipv6_non_vm_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM
        """
        dummy_nic = conf.HOST_0_NICS[-8]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_5
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_5,
                    "nic": dummy_nic,
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

    @polarion("RHEVM-16643")
    def test_06_static_ipv6_non_vm_vlan_network_on_host(self):
        """
        Attach network with static IPv6 over Non-VM VLAN
        """
        dummy_nic = conf.HOST_0_NICS[-9]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_6
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_6,
                    "nic": dummy_nic,
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

    @polarion("RHEVM-16884")
    def test_07_edit_network_with_ipv4_and_ipv6_addresses(self):
        """
        Edit network with ipv4 and ipv6 addresses
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV4_AND_IPV6_DICT["ipv6"]["address"] = self.ip_v6_7
        net_api_conf.BASIC_IPV4_AND_IPV6_DICT["ipv4"]["address"] = self.ip_v4_7
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV4_AND_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Edit network %s with IPv4 and IPv6 addresses %s",
            self.net_1, net_api_conf.BASIC_IPV4_AND_IPV6_DICT
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM-16899")
    def test_08_change_static_ipv6_address_with_static_ipv6_address(self):
        """
        Change the static ipv6 address with other static ipv6 address
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_8
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Change network %s ipv6 static address with other static ipv6 "
            "address %s",
            self.net_1, net_api_conf.BASIC_IPV6_DICT
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM-16900")
    def test_09_change_the_ipv6_bootproto_to_dhcpv6(self):
        """
        Change the ipv6 boot protocol to DHCP v6
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV6_DICT["ip"]["boot_protocol"] = "dhcp"
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = None
        net_api_conf.BASIC_IPV6_DICT["ip"]["netmask"] = None
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Change network %s ipv6 boot protocol to DHCP v6", self.net_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM-16901")
    def test_10_change_the_ipv6_bootproto_to_autoconf(self):
        """
        Change the ipv6 boot protocol to autoconf
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV6_DICT["ip"]["boot_protocol"] = "autoconf"
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = None
        net_api_conf.BASIC_IPV6_DICT["ip"]["netmask"] = None

        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Change network %s ipv6 boot protocol to autoconf", self.net_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM-16902")
    def test_11_change_the_ipv6_bootproto_to_static(self):
        """
        Change the ipv6 boot protocol to static
        """
        dummy_nic = conf.HOST_0_NICS[-1]
        net_api_conf.BASIC_IPV6_DICT["ip"]["boot_protocol"] = "static"
        net_api_conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_9
        net_api_conf.BASIC_IPV6_DICT["ip"]["netmask"] = "24"
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": dummy_nic,
                    "ip": net_api_conf.BASIC_IPV6_DICT
                },
            }
        }
        testflow.step(
            "Change network %s ipv6 boot protocol to static", self.net_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
