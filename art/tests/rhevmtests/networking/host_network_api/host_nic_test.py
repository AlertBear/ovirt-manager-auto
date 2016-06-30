#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host NIC href
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as conf
import helper
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    host_nic_case_08, host_nic_case_09, host_nic_case_10, host_nic_case_11,
    host_nic_case_12, host_nic_case_15, teardown_all_cases_host_nic
)

logger = logging.getLogger("Host_Network_API_Host_NIC_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic01(NetworkTest):
    """
    Attach network to host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[1][0]

    @polarion("RHEVM3-9601")
    def test_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": self.net
        }
        testflow.step("Attach network to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic02(NetworkTest):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[2][0]

    @polarion("RHEVM3-9619")
    def test_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net
        }
        testflow.step("Attach VLAN network to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic03(NetworkTest):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[3][0]

    @polarion("RHEVM3-9618")
    def test_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": self.net
        }
        testflow.step("Attach non-VM network to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic04(NetworkTest):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[0]
    ip_prefix = conf.IPS[1]
    net_1 = conf.NIC_NETS[4][0]
    net_2 = conf.NIC_NETS[4][1]

    @polarion("RHEVM3-10446")
    def test_ip_netmask_network_on_host_nic(self):
        """
        Attach network with IP (netmask) to host NIC
        Attach network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach network with IP (netmask) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )

    def test_ip_prefix_network_on_host_nic(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach network with IP (prefix) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[2], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic05(NetworkTest):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[4]
    ip_prefix = conf.IPS[5]
    net_1 = conf.NIC_NETS[5][0]
    net_2 = conf.NIC_NETS[5][1]

    @polarion("RHEVM3-10447")
    def test_ip_netmask_vlan_network_on_host_nic(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach VLAN network with IP (netmask) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )

    def test_ip_prefix_vlan_network_on_host_nic(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach VLAN network with IP (prefix) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[2], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic06(NetworkTest):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[2]
    ip_prefix = conf.IPS[3]
    net_1 = conf.NIC_NETS[6][0]
    net_2 = conf.NIC_NETS[6][1]

    @polarion("RHEVM3-10448")
    def test_ip_netmask_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Attach Non-VM network with IP (netmask) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )

    def test_ip_prefix_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Attach Non-VM network with IP (prefix) to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[2], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic07(NetworkTest):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[7][0]

    @polarion("RHEVM3-10450")
    def test_network_custom_properties_on_host_nic(self):
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
            "properties": properties_dict
        }
        testflow.step("Attach network with custom properties to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_08.__name__)
class TestHostNetworkApiHostNic08(NetworkTest):
    """
    Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True
    net_2 = conf.NIC_NETS[8][1]

    @polarion("RHEVM3-10451")
    def test_network_mtu_on_host_nic(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2
        }
        testflow.step(
            "Negative: Try to attach VLAN network with 9000 MTU size to the "
            "same NIC"
        )
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], positive=False,
                **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_09.__name__)
class TestHostNetworkApiHostNic09(NetworkTest):
    """
    Remove network from host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[9][0]

    @polarion("RHEVM3-10452")
    def test_network_remove_from_host_nic(self):
        """
        Remove network from host NIC
        """
        testflow.step("Remove network from host NIC")
        self.assertTrue(
            hl_host_network.remove_networks_from_host(
                host_name=net_conf.HOST_0_NAME, networks=[self.net],
                nic=net_conf.HOST_0_NICS[1]
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_10.__name__)
class TestHostNetworkApiHostNic10(NetworkTest):
    """
    Update the network to have IP (netmask)
    Update the network to have IP (prefix)
    """
    __test__ = True
    ip_netmask = conf.IPS[8]
    ip_prefix = conf.IPS[9]
    net_1 = conf.NIC_NETS[10][0]
    net_2 = conf.NIC_NETS[10][1]

    @polarion("RHEVM3-10453")
    def test_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_nic_1_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step("Update the network to have IP (netmask)")
        self.assertTrue(
            hl_host_network.update_network_on_host(
                host_name=net_conf.HOST_0_NAME, nic=net_conf.HOST_0_NICS[1],
                **network_host_nic_1_api_dict
            )
        )

    @polarion("RHEVM3-10453")
    def test_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_nic_1_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step("Update the network to have IP (prefix)")
        self.assertTrue(
            hl_host_network.update_network_on_host(
                host_name=net_conf.HOST_0_NAME, nic=net_conf.HOST_0_NICS[2],
                **network_host_nic_1_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_11.__name__)
class TestHostNetworkApiHostNic11(NetworkTest):
    """
    Attach network to BOND
    """
    __test__ = True
    bond = "bond11"
    net = conf.NIC_NETS[11][0]

    @polarion("RHEVM3-10454")
    def test_network_on_bond_host_nic(self):
        """
        Attach network on BOND
        """
        network_host_api_dict = {
            "network": self.net
        }
        testflow.step("Attach network on BOND")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=self.bond, **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_12.__name__)
class TestHostNetworkApiHostNic12(NetworkTest):
    """
    Delete 2 networks from the BOND
    """
    __test__ = True
    net_2 = conf.NIC_NETS[12][1]
    net_3 = conf.NIC_NETS[12][2]
    net_list_to_remove = [net_2, net_3]

    @polarion("RHEVM3-10455")
    def test_remove_networks_from_bond_host_nic(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host NIC
        """
        testflow.step("Delete 2 networks from the BOND")
        for net in self.net_list_to_remove:
            self.assertTrue(
                hl_host_network.remove_networks_from_host(
                    host_name=net_conf.HOST_0_NAME, networks=[net]
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic13(NetworkTest):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[13][0]

    @polarion("RHEVM3-9620")
    def test_non_vm_vlan_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": self.net
        }
        testflow.step("Attach Non-VM VLAN network to host NIC")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(teardown_all_cases_host_nic.__name__)
class TestHostNetworkApiHostNic14(NetworkTest):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[6]
    ip_prefix = conf.IPS[7]
    net_1 = conf.NIC_NETS[14][0]
    net_2 = conf.NIC_NETS[14][1]

    @polarion("RHEVM3-10449")
    def test_non_vm_vlan_ip_netmask_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "network": self.net_1,
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        testflow.step(
            "Attach Non-VM VLAN network with IP (netmask) to host NIC"
        )
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[1], **network_host_api_dict
            )
        )

    @polarion("RHEVM3-10449")
    def test_non_vm_vlan_ip_prefix_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        testflow.step(
            "Attach Non-VM VLAN network with IP (prefix) to host NIC"
        )
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=net_conf.HOST_0_NICS[2], **network_host_api_dict
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(host_nic_case_15.__name__)
class TestHostNetworkApiHostNic15(NetworkTest):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True
    bond = "bond15"
    net = conf.NIC_NETS[15][0]

    @polarion("RHEVM3-11878")
    def test_network_custom_properties_on_bond_host_nic(self):
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
            "properties": properties_dict
        }
        testflow.step("Attach network with custom properties to BOND")
        self.assertTrue(
            helper.attach_network_attachment(
                host_nic=self.bond, **network_host_api_dict
            )
        )
