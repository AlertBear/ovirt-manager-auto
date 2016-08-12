#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host href
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import config as conf
import helper
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    teardown_all_cases_host, host_case_08, host_case_09, host_case_10,
    host_case_11, host_case_12, host_case_13, host_case_16, host_case_17,
    host_case_18
)

logger = logging.getLogger("Host_Network_API_Host_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost01(NetworkTest):
    """
    Attach network to host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[1][0]

    @polarion("RHEVM3-10456")
    def test_network_on_host(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": net_conf.HOST_0_NICS[1]
        }
        testflow.step("Attach network to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost02(NetworkTest):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[2][0]

    @polarion("RHEVM3-10458")
    def test_vlan_network_on_host(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": net_conf.HOST_0_NICS[1]
        }
        testflow.step("Attach VLAN network to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost03(NetworkTest):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[3][0]

    @polarion("RHEVM3-10457")
    def test_non_vm_network_on_host(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": net_conf.HOST_0_NICS[1]
        }
        testflow.step("Attach Non-VM network to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost04(NetworkTest):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[10]
    ip_prefix = conf.IPS[11]
    net_1 = conf.HOST_NETS[4][0]
    net_2 = conf.HOST_NETS[4][1]

    @polarion("RHEVM3-10460")
    def test_ip_netmask_network_on_host(self):
        """
        Attach network with IP to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "nic": net_conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach network with IP (netmask) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10460")
    def test_ip_prefix_network_on_host(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": net_conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach network with IP (prefix) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost05(NetworkTest):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[14]
    ip_prefix = conf.IPS[15]
    net_1 = conf.HOST_NETS[5][0]
    net_2 = conf.HOST_NETS[5][1]

    @polarion("RHEVM3-10461")
    def test_ip_netmask_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "nic": net_conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach VLAN network with IP (netmask) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10461")
    def test_ip_prefix_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": net_conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach VLAN network with IP (prefix) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost06(NetworkTest):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[12]
    ip_prefix = conf.IPS[13]
    net_1 = conf.HOST_NETS[6][0]
    net_2 = conf.HOST_NETS[6][1]

    @polarion("RHEVM3-10462")
    def test_ip_netmask_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "nic": net_conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach Non-VM network with IP (netmask) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10462")
    def test_ip_prefix_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": net_conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach Non-VM network with IP (prefix) to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost07(NetworkTest):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[7][0]

    @polarion("RHEVM3-10464")
    def test_network_custom_properties_on_host(self):
        """
        Attach network with custom properties to host NIC
        """
        properties_dict = {
            "bridge_opts": net_conf.PRIORITY,
            "ethtool_opts": net_conf.TX_CHECKSUM.format(
                nic=net_conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net,
            "nic": net_conf.HOST_0_NICS[1],
            "properties": properties_dict
        }
        testflow.step("Attach network with custom properties to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(host_case_08.__name__)
class TestHostNetworkApiHost08(NetworkTest):
    """
    Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True
    net_2 = conf.HOST_NETS[8][1]

    @polarion("RHEVM3-10465")
    def test_network_mtu_on_host(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2,
            "nic": net_conf.HOST_0_NICS[1]
        }
        testflow.step(
            "Negative: Try to attach VLAN network with 9000 MTU size to the "
            "same NIC"
        )
        assert helper.attach_network_attachment(
            positive=False, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_case_09.__name__)
class TestHostNetworkApiHost09(NetworkTest):
    """
    Remove network from host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[9][0]

    @polarion("RHEVM3-10466")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        testflow.step("Remove network from host NIC")
        assert hl_host_network.remove_networks_from_host(
            host_name=net_conf.HOST_0_NAME, networks=[self.net]
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_case_10.__name__)
class TestHostNetworkApiHost10(NetworkTest):
    """
    Update the network to have IP (netmask)
    Update the network to have IP (prefix)
    """
    __test__ = True
    ip_netmask = conf.IPS[18]
    ip_prefix = conf.IPS[19]
    net_1 = conf.HOST_NETS[10][0]
    net_2 = conf.HOST_NETS[10][1]

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Update the network to have IP (netmask)")
        assert hl_host_network.update_network_on_host(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Update the network to have IP (prefix)")
        assert hl_host_network.update_network_on_host(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_case_11.__name__)
class TestHostNetworkApiHost11(NetworkTest):
    """
    Attach network to BOND
    """
    __test__ = True
    bond = "bond11"
    net = conf.HOST_NETS[11][0]

    @polarion("RHEVM3-10468")
    def test_attach_network_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": self.bond
        }
        testflow.step("Attach network to BOND")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(host_case_12.__name__)
class TestHostNetworkApiHost12(NetworkTest):
    """
    Delete 2 networks from the BOND
    """
    __test__ = True
    net_2 = conf.HOST_NETS[12][1]
    net_3 = conf.HOST_NETS[12][2]
    net_list_to_remove = [net_2, net_3]

    @polarion("RHEVM3-10469")
    def test_remove_networks_from_bond_host(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host
        """
        testflow.step("Delete 2 networks from the BOND")
        for net in self.net_list_to_remove:
            assert hl_host_network.remove_networks_from_host(
                host_name=net_conf.HOST_0_NAME, networks=[net]
            )


@attr(tier=2)
@pytest.mark.usefixtures(host_case_13.__name__)
class TestHostNetworkApiHost13(NetworkTest):
    """
    Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_net_13"

    @polarion("RHEVM3-12165")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step("Remove the unmanaged network from host")
        assert ll_host_network.remove_unmanaged_networks(
            host_name=net_conf.HOST_0_NAME, networks=[self.unmamanged_net]
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost14(NetworkTest):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[14][0]

    @polarion("RHEVM3-10459")
    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": net_conf.HOST_0_NICS[1]
        }
        testflow.step("Attach Non-VM VLAN network to host NIC")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host.__name__)
class TestHostNetworkApiHost15(NetworkTest):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[16]
    ip_prefix = conf.IPS[17]
    net_1 = conf.HOST_NETS[15][0]
    net_2 = conf.HOST_NETS[15][1]

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "nic": net_conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM VLAN network with IP (netmask) to host NIC"
        )
        assert helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_prefix_on_host(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": net_conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM VLAN network with IP (prefix) to host NIC"
        )
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(host_case_16.__name__)
class TestHostNetworkApiHost16(NetworkTest):
    """
    Remove the unmanaged network from host (BOND)
    """
    __test__ = True
    unmamanged_net = "unman_host16"

    @polarion("RHEVM3-12166")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step("Remove the unmanaged network from host (BOND)")
        assert ll_host_network.remove_unmanaged_networks(
            host_name=net_conf.HOST_0_NAME, networks=[self.unmamanged_net]
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_case_17.__name__)
class TestHostNetworkApiHost17(NetworkTest):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True
    bond = "bond17"
    net = conf.HOST_NETS[17][0]

    @polarion("RHEVM3-11879")
    def test_network_custom_properties_on_bond_host(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": net_conf.PRIORITY,
            "ethtool_opts": net_conf.TX_CHECKSUM.format(
                nic=net_conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net,
            "nic": self.bond,
            "properties": properties_dict
        }
        testflow.step("Attach network with custom properties to BOND")
        assert helper.attach_network_attachment(**network_host_api_dict)


@attr(tier=2)
@pytest.mark.usefixtures(host_case_18.__name__)
class TestHostNetworkApiHost18(NetworkTest):
    """
    Attach VM network to host NIC that has VLAN network on it
    Attach VLAN network to host NIC that has VM network on it
    """
    __test__ = True
    net_case_vlan = conf.HOST_NETS[18][2]
    net_case_vm = conf.HOST_NETS[18][3]

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vlan,
            "nic": net_conf.HOST_0_NICS[1],
        }
        testflow.step(
            "Attach VLAN network to host NIC that has VM network on it"
        )
        assert helper.attach_network_attachment(**network_host_api_dict)

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vm,
            "nic": net_conf.HOST_0_NICS[2],
        }
        testflow.step(
            "Attach VLAN network to host NIC that has VM network on it"
        )
        assert helper.attach_network_attachment(**network_host_api_dict)
