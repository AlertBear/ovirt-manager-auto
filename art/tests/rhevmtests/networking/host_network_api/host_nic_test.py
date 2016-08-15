#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host NIC href
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import attach_net_to_host
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)


@pytest.fixture(scope="module", autouse=True)
def host_nic_api_prepare_setup(request):
    """
    Prepare setup for host_nic tests
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
        networks_dict=net_api_conf.NIC_DICT, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(clean_host_interfaces.__name__)
class TestHostNetworkApiHostNic01(NetworkTest):
    """
    1) Attach network to host NIC.
    2) Attach VLAN network to host NIC.
    3) Attach Non-VM network to host NIC.
    4) Attach network with IP (netmask) to host NIC.
    5) Attach network with IP (prefix) to host NIC.
    6) Attach VLAN network with IP (netmask) to host NIC
    7) Attach VLAN network with IP (prefix) to host NIC
    8) Attach Non-VM network with IP (netmask) to host NIC.
    9) Attach Non-VM network with IP (prefix) to host NIC.
    10) Attach network with custom properties to host NIC.
    11) Attach Non-VM VLAN network to host NIC.
    12) Attach Non-VM VLAN network with IP (netmask) to host NIC.
    13) Attach Non-VM VLAN network with IP (prefix) to host NIC.
    """
    __test__ = True
    net_1 = net_api_conf.NIC_NETS[1][0]
    net_2 = net_api_conf.NIC_NETS[1][1]
    net_3 = net_api_conf.NIC_NETS[1][2]
    net_4 = net_api_conf.NIC_NETS[1][3]
    ip_netmask_net_4 = net_api_conf.IPS[0]
    net_5 = net_api_conf.NIC_NETS[1][4]
    ip_prefix_net_5 = net_api_conf.IPS[1]
    net_6 = net_api_conf.NIC_NETS[1][5]
    ip_netmask_net_6 = net_api_conf.IPS[4]
    net_7 = net_api_conf.NIC_NETS[1][6]
    ip_prefix_net_7 = net_api_conf.IPS[5]
    net_8 = net_api_conf.NIC_NETS[1][7]
    ip_netmask_net_8 = net_api_conf.IPS[2]
    net_9 = net_api_conf.NIC_NETS[1][8]
    ip_prefix_net_9 = net_api_conf.IPS[3]
    net_10 = net_api_conf.NIC_NETS[1][9]
    net_11 = net_api_conf.NIC_NETS[1][10]
    net_12 = net_api_conf.NIC_NETS[1][11]
    ip_netmask_net_12 = net_api_conf.IPS[6]
    net_13 = net_api_conf.NIC_NETS[1][12]
    ip_prefix_net_13 = net_api_conf.IPS[7]
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-9601")
    def test_01_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_1
        }
        testflow.step(
            "Attach network %s to host NIC %s", self.net_1, conf.HOST_0_NICS[1]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[1],
            **network_host_api_dict
        )

    @polarion("RHEVM3-9619")
    def test_02_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_2
        }
        testflow.step(
            "Attach VLAN network %s to host NIC %s",
            self.net_2, conf.HOST_0_NICS[2]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[2],
            **network_host_api_dict
        )

    @polarion("RHEVM3-9618")
    def test_03_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_3
        }
        testflow.step(
            "Attach non-VM network %s to host NIC %s", self.net_3,
            conf.HOST_0_NICS[3]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[3],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10446")
    def test_04_ip_netmask_network_on_host_nic(self):
        """
        Attach network with IP (netmask) to host NIC
        Attach network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_4
        )
        network_host_api_dict = {
            "network": self.net_4,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach network %s with IP (netmask) %s to host NIC %s",
            self.net_4, self.ip_netmask_net_4, conf.HOST_0_NICS[4]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[4],
            **network_host_api_dict
        )

    def test_05_ip_prefix_network_on_host_nic(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_5
        )
        network_host_api_dict = {
            "network": self.net_5,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach network %s with IP (prefix) %s to host NIC %s",
            self.net_5, self.ip_prefix_net_5, conf.HOST_0_NICS[5]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[5],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10447")
    def test_06_ip_netmask_vlan_network_on_host_nic(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_6
        )
        network_host_api_dict = {
            "network": self.net_6,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach VLAN network %s with IP (netmask) %s to host NIC %s",
            self.net_6, self.ip_netmask_net_6, conf.HOST_0_NICS[6]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[6],
            **network_host_api_dict
        )

    def test_07_ip_prefix_vlan_network_on_host_nic(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_7
        )
        network_host_api_dict = {
            "network": self.net_7,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach VLAN network %s with IP (prefix) %s to host NIC %s",
            self.net_7, self.ip_prefix_net_7, conf.HOST_0_NICS[7]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[7],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10448")
    def test_08_ip_netmask_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_8
        )
        network_host_api_dict = {
            "network": self.net_8,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM network %s with IP (netmask) %s to host NIC %s",
            self.net_8, self.ip_netmask_net_8, conf.HOST_0_NICS[8]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[8],
            **network_host_api_dict
        )

    def test_09_ip_prefix_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_9
        )
        network_host_api_dict = {
            "network": self.net_9,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM network %s with IP (prefix) %s to host NIC %s",
            self.net_9, self.ip_prefix_net_9, conf.HOST_0_NICS[9]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[9],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10450")
    def test_10_network_custom_properties_on_host_nic(self):
        """
        Attach network with custom properties to host NIC
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[10], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net_10,
            "properties": properties_dict
        }
        testflow.step(
            "Attach network %s with custom properties %s to host NIC %s",
            self.net_10, properties_dict, conf.HOST_0_NICS[10]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[10],
            **network_host_api_dict
        )

    @polarion("RHEVM3-9620")
    def test_11_non_vm_vlan_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net_11
        }
        testflow.step(
            "Attach Non-VM VLAN network %s to host NIC %s", self.net_11,
            conf.HOST_0_NICS[11]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[11],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10449")
    def test_12_non_vm_vlan_ip_netmask_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_12
        )
        network_host_api_dict = {
            "network": self.net_12,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM VLAN network %s with IP (netmask) %s "
            "to host NIC %s", self.net_12, self.ip_netmask_net_12,
            conf.HOST_0_NICS[12]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[12],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10449")
    def test_13_non_vm_vlan_ip_prefix_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_13
        )
        network_host_api_dict = {
            "network": self.net_13,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM VLAN network %s with IP (prefix) %s to host NIC %s",
            self.net_13, self.ip_prefix_net_13, conf.HOST_0_NICS[13]
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[13],
            **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_net_to_host.__name__,
    clean_host_interfaces.__name__
)
class TestHostNetworkApiHostNic02(NetworkTest):
    """
    1) Negative: Try to attach VLAN network with 9000 MTU size to the same NIC.
    2) Remove network from host NIC.
    """
    __test__ = True
    net_1 = net_api_conf.NIC_NETS[2][0]
    net_2 = net_api_conf.NIC_NETS[2][1]
    net_3 = net_api_conf.NIC_NETS[2][2]
    sn_dict = {
        1: {
            "network": net_1,
            "nic": None
        },
        2: {
            "network": net_3,
            "nic": None
        }
    }

    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-10451")
    def test_01_network_mtu_on_host_nic(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2
        }
        testflow.step(
            "Negative: Try to attach VLAN network %s with 9000 MTU size to the"
            "same NIC %s"
        )
        assert not hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=conf.HOST_0_NICS[1],
            **network_host_api_dict
        )

    @polarion("RHEVM3-10452")
    def test_02_network_remove_from_host_nic(self):
        """
        Remove network from host NIC
        """
        testflow.step(
            "Remove network %s from host NIC %s", self.net_3,
            conf.HOST_0_NICS[2]
        )
        assert hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_3],
            nic=conf.HOST_0_NICS[2]
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiHostNic03(NetworkTest):
    """
    1) Update the network to have IP (netmask).
    2) Update the network to have IP (prefix).
    3) Attach network to BOND.
    4) Delete 2 networks from the BOND.
    5) Attach network with custom properties to BOND.
    """
    __test__ = True
    net_1 = net_api_conf.NIC_NETS[3][0]
    net_2 = net_api_conf.NIC_NETS[3][1]
    net_3 = net_api_conf.NIC_NETS[3][2]
    net_4 = net_api_conf.NIC_NETS[3][3]
    net_5 = net_api_conf.NIC_NETS[3][4]
    net_6 = net_api_conf.NIC_NETS[3][5]
    net_7 = net_api_conf.NIC_NETS[3][6]
    net_list_to_remove = [net_5, net_6]
    ip_netmask = net_api_conf.IPS[8]
    ip_prefix = net_api_conf.IPS[9]
    bond_1 = "bond11"
    bond_2 = "bond12"
    bond_3 = "bond15"

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
            }
        }
    }

    @polarion("RHEVM3-10453")
    def test_01_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_nic_1_api_dict = {
            "network": self.net_1,
            "ip": net_api_conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Update the network %s to have IP (netmask) %s", self.net_1,
            self.ip_netmask
        )
        assert hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1],
            **network_host_nic_1_api_dict
        )

    @polarion("RHEVM3-10453")
    def test_02_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_nic_1_api_dict = {
            "network": self.net_2,
            "ip": net_api_conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Update the network %s to have IP (prefix) %s", self.net_2,
            self.ip_prefix
        )
        assert hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[2],
            **network_host_nic_1_api_dict
        )

    @polarion("RHEVM3-10454")
    def test_03_network_on_bond_host_nic(self):
        """
        Attach network on BOND
        """
        network_host_api_dict = {
            "network": self.net_3
        }
        testflow.step("Attach network %s on BOND %s", self.net_3, self.bond_1)
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=self.bond_1,
            **network_host_api_dict
        )

    @polarion("RHEVM3-10455")
    def test_04_remove_networks_from_bond_host_nic(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host NIC
        """
        testflow.step(
            "Delete 2 networks %s from the BOND %s", self.net_list_to_remove,
            self.bond_2
        )
        for net in self.net_list_to_remove:
            assert hl_host_network.remove_networks_from_host(
                host_name=conf.HOST_0_NAME, networks=[net], nic=self.bond_2
            )

    @polarion("RHEVM3-11878")
    def test_05_network_custom_properties_on_bond_host_nic(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net_7,
            "properties": properties_dict
        }
        testflow.step(
            "Attach network %s with custom properties %s to BOND %s",
            self.net_7, properties_dict, self.bond_3
        )
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=self.bond_3,
            **network_host_api_dict
        )
