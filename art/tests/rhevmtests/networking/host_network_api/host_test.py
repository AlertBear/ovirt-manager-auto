#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host href
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.network_custom_properties.config as cust_prop_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    attach_net_to_host, create_network_in_dc_and_cluster, remove_network
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)


@pytest.fixture(scope="module", autouse=True)
def host_api_prepare_setup(request):
    """
    Prepare setup for host tests.
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Remove networks from setup.
        """
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=net_api_conf.HOST_DICT, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(clean_host_interfaces.__name__)
class TestHostNetworkApiHost01(NetworkTest):
    """
    1) Attach network to host NIC.
    2) Attach VLAN network to host NIC.
    3) Attach Non-VM network to host NIC.
    4) Attach network with IP (netmask) to host NIC.
    5) Attach network with IP (prefix) to host NIC.
    6) Attach VLAN network with IP (netmask) to host NIC.
    7) Attach VLAN network with IP (prefix) to host NIC.
    8) Attach Non-VM network with IP (netmask) to host NIC.
    9) Attach Non-VM network with IP (prefix) to host NIC.
    10) Attach network with custom properties to host NIC.
    11) Attach Non-VM VLAN network to host NIC
    12) Attach Non-VM VLAN network with IP (netmask) to host NIC
    13 )Attach Non-VM VLAN network with IP (prefix) to host NIC

    """
    __test__ = True
    net_1 = net_api_conf.HOST_NETS[1][0]
    net_2 = net_api_conf.HOST_NETS[1][1]
    net_3 = net_api_conf.HOST_NETS[1][2]
    net_4 = net_api_conf.HOST_NETS[1][3]
    ip_netmask_net_4 = net_api_conf.IPS[10]
    net_5 = net_api_conf.HOST_NETS[1][4]
    ip_prefix_net_5 = net_api_conf.IPS[11]
    net_6 = net_api_conf.HOST_NETS[1][5]
    ip_netmask_net_6 = net_api_conf.IPS[14]
    net_7 = net_api_conf.HOST_NETS[1][6]
    ip_prefix_net_7 = net_api_conf.IPS[15]
    net_8 = net_api_conf.HOST_NETS[1][7]
    ip_netmask_net_8 = net_api_conf.IPS[12]
    net_9 = net_api_conf.HOST_NETS[1][8]
    ip_prefix_net_9 = net_api_conf.IPS[13]
    net_10 = net_api_conf.HOST_NETS[1][9]
    net_11 = net_api_conf.HOST_NETS[1][10]
    net_12 = net_api_conf.HOST_NETS[1][11]
    ip_netmask_net_12 = net_api_conf.IPS[16]
    net_13 = net_api_conf.HOST_NETS[1][12]
    ip_prefix_net_13 = net_api_conf.IPS[17]
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-10456")
    def test_network_on_host(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_1,
            "nic": conf.HOST_0_NICS[1]
        }
        testflow.step(
            "Attach network %s to host NIC %s", self.net_1,
            conf.HOST_0_NICS[1]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10458")
    def test_vlan_network_on_host(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[2]
        }
        testflow.step(
            "Attach VLAN network %s to host NIC %s",  self.net_2,
            conf.HOST_0_NICS[2]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10457")
    def test_non_vm_network_on_host(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_3,
            "nic": conf.HOST_0_NICS[3]
        }
        testflow.step(
            "Attach Non-VM network %s to host NIC %s", self.net_3,
            conf.HOST_0_NICS[3]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10460")
    def test_ip_netmask_network_on_host(self):
        """
        Attach network with IP to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_4
        )
        network_host_api_dict = {
            "network": self.net_4,
            "nic": conf.HOST_0_NICS[4],
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach network %s with IP (netmask) %s to host NIC %s",
            self.net_4, net_api_conf.BASIC_IP_DICT_NETMASK,
            conf.HOST_0_NICS[4]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10460")
    def test_ip_prefix_network_on_host(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_5
        )
        network_host_api_dict = {
            "network": self.net_5,
            "nic": conf.HOST_0_NICS[5],
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach network %s with IP (prefix) %s to host NIC %s",
            self.net_5, net_api_conf.BASIC_IP_DICT_PREFIX,
            conf.HOST_0_NICS[5]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10461")
    def test_ip_netmask_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_6
        )
        network_host_api_dict = {
            "network": self.net_6,
            "nic": conf.HOST_0_NICS[6],
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach VLAN network %s with IP (netmask) %s to host NIC %s",
            self.net_6, net_api_conf.BASIC_IP_DICT_NETMASK,
            conf.HOST_0_NICS[6]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10461")
    def test_ip_prefix_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_7
        )
        network_host_api_dict = {
            "network": self.net_7,
            "nic": conf.HOST_0_NICS[7],
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach VLAN network %s with IP (prefix) %s to host NIC %s",
            self.net_7, conf.HOST_0_NICS[7],
            net_api_conf.BASIC_IP_DICT_PREFIX
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10462")
    def test_ip_netmask_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_8
        )
        network_host_api_dict = {
            "network": self.net_8,
            "nic": conf.HOST_0_NICS[8],
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM network %s with IP (netmask) %s to host NIC %s",
            self.net_8, net_api_conf.BASIC_IP_DICT_NETMASK,
            conf.HOST_0_NICS[8]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10462")
    def test_ip_prefix_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_9
        )
        network_host_api_dict = {
            "network": self.net_9,
            "nic": conf.HOST_0_NICS[9],
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM network %s with IP (prefix) %s to host NIC %s",
            self.net_9, net_api_conf.BASIC_IP_DICT_PREFIX,
            conf.HOST_0_NICS[9]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10464")
    def test_network_custom_properties_on_host(self):
        """
        Attach network with custom properties to host NIC
        """
        properties_dict = {
            "bridge_opts": cust_prop_conf.PRIORITY,
            "ethtool_opts": cust_prop_conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[10], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net_10,
            "nic": conf.HOST_0_NICS[10],
            "properties": properties_dict
        }
        testflow.step(
            "Attach network %s with custom properties %s to host NIC %s",
            self.net_10, properties_dict, conf.HOST_0_NICS[10]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10459")
    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_11,
            "nic": conf.HOST_0_NICS[11]
        }
        testflow.step(
            "Attach Non-VM VLAN network  %s to host NIC %s", self.net_11,
            conf.HOST_0_NICS[11]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_12
        )
        network_host_api_dict = {
            "network": self.net_12,
            "nic": conf.HOST_0_NICS[12],
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM VLAN network %s with IP (netmask) %s to host"
            "NIC %s", self.net_12, net_api_conf.BASIC_IP_DICT_NETMASK,
            conf.HOST_0_NICS[12]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_prefix_on_host(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_13
        )
        network_host_api_dict = {
            "network": self.net_13,
            "nic": conf.HOST_0_NICS[13],
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM VLAN network %s with IP (prefix) %s to host NIC %s",
            self.net_12, net_api_conf.BASIC_IP_DICT_PREFIX,
            conf.HOST_0_NICS[13]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_net_to_host.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApiHost02(NetworkTest):
    """
    1) Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    2) Remove network from host NIC.
    """
    __test__ = True
    net_1 = net_api_conf.HOST_NETS[2][0]
    net_2 = net_api_conf.HOST_NETS[2][1]
    net_3 = net_api_conf.HOST_NETS[2][2]
    sn_dict = {
        1: {
            "network": net_1,
            "nic": 1
        },
        2: {
            "network": net_3,
            "nic": 2
        }
    }
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-10465")
    def test_network_mtu_on_host(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[1]
        }
        testflow.step(
            "Negative: Try to attach VLAN network %s with 9000 MTU size to the"
            "same NIC %s", self.net_2, conf.HOST_0_NICS[1]
        )
        assert not hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10466")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        testflow.step("Remove network %s from host NIC", self.net_3)
        assert hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_3]
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiHost03(NetworkTest):
    """
    1) Update the network to have IP (netmask)
    2) Update the network to have IP (prefix)
    3) Attach network to BOND
    4) Delete 2 networks from the BOND
    5) Attach network with custom properties to BOND
    6) Attach VM network to host NIC that has VLAN network on it
    7) Attach VLAN network to host NIC that has VM network on it
    """
    __test__ = True
    ip_netmask = net_api_conf.IPS[18]
    ip_prefix = net_api_conf.IPS[19]
    bond_1 = "bond31"
    bond_2 = "bond32"
    bond_3 = "bond33"
    net_1 = net_api_conf.HOST_NETS[3][0]
    net_2 = net_api_conf.HOST_NETS[3][1]
    net_3 = net_api_conf.HOST_NETS[3][2]
    net_4 = net_api_conf.HOST_NETS[3][3]
    net_5 = net_api_conf.HOST_NETS[3][4]
    net_6 = net_api_conf.HOST_NETS[3][5]
    net_list_to_remove = [net_5, net_6]
    net_7 = net_api_conf.HOST_NETS[3][6]
    net_8 = net_api_conf.HOST_NETS[3][7]
    net_9 = net_api_conf.HOST_NETS[3][8]
    net_case_vlan = net_api_conf.HOST_NETS[3][9]
    net_case_vm = net_api_conf.HOST_NETS[3][10]

    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 2,
                "network": net_2
            },
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4]
            },
            net_4: {
                "nic": bond_2,
                "network": net_4
            },
            net_5: {
                "nic": bond_2,
                "network": net_5
            },
            net_6: {
                "nic": bond_2,
                "network": net_6
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-5, -6]
            },
            net_8: {
                "nic": 3,
                "network": net_8
            },
            net_9: {
                "nic": 4,
                "network": net_9
            }
        }
    }

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Update the network %s to have IP (netmask) %s", self.net_1,
            net_api_conf.BASIC_IP_DICT_NETMASK
        )
        assert hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Update the network %s to have IP (prefix) %s", self.net_2,
            net_api_conf.BASIC_IP_DICT_PREFIX
        )
        assert hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10468")
    def test_attach_network_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "network": self.net_3,
            "nic": self.bond_1
        }
        testflow.step("Attach network %s to BOND %s", self.net_3, self.bond_1)
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10469")
    def test_remove_networks_from_bond_host(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host
        """
        testflow.step(
            "Delete 2 networks %s from the BOND %s", self.net_list_to_remove,
            self.bond_2
        )
        for net in self.net_list_to_remove:
            assert hl_host_network.remove_networks_from_host(
                host_name=conf.HOST_0_NAME, networks=[net]
            )

    @polarion("RHEVM3-11879")
    def test_network_custom_properties_on_bond_host(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": cust_prop_conf.PRIORITY,
            "ethtool_opts": cust_prop_conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net_7,
            "nic": self.bond_3,
            "properties": properties_dict
        }
        testflow.step(
            "Attach network %s with custom properties %s to BOND %s",
            self.net_7, properties_dict, self.bond_3
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vlan,
            "nic": conf.HOST_0_NICS[3],
        }
        testflow.step(
            "Attach VLAN network %s to host NIC %s that has VM network on it",
            self.net_case_vlan, conf.HOST_0_NICS[3]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vm,
            "nic": conf.HOST_0_NICS[4],
        }
        testflow.step(
            "Attach VLAN network %s to host NIC %s that has VM network on it",
            self.net_case_vm, conf.HOST_0_NICS[4]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_in_dc_and_cluster.__name__,
    attach_net_to_host.__name__,
    remove_network.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApiHost04(NetworkTest):
    """
    Remove the unmanaged network from host
    """
    __test__ = True
    net_list = ["unman_net_04"]
    net = "unman_net_04"
    nic = 1
    sn_dict = {
        1: {
            "network": net,
            "nic": 1
        }
    }
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-12165")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step(
            "Get unmanaged network %s object from host %s"
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )
        testflow.step(
            "Remove the unmanaged network %s from host %s", self.net,
            conf.HOST_0_NAME
        )
        assert ll_host_network.remove_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_in_dc_and_cluster.__name__,
    setup_networks_fixture.__name__,
    remove_network.__name__,
)
class TestHostNetworkApiHost05(NetworkTest):
    """
    Remove the unmanaged network from host (BOND)
    """
    __test__ = True
    net = "unman_host05"
    bond = "bond05"
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [-1, -2]
            },
            net: {
                "nic": bond,
                "network": net
            },

        }
    }

    @polarion("RHEVM3-12166")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step(
            "Get unmanaged network %s object from host %s"
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )
        testflow.step(
            "Remove the unmanaged network %s from host (BOND) %s",
            self.net, self.bond
        )
        assert ll_host_network.remove_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )
