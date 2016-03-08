#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host NIC href
"""

import helper
import logging
import config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Host_NIC_Cases")


def setup_module():
    """
    Add networks
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NIC_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks
    """
    network_helper.remove_networks_from_setup()


class TestHostNetworkApiHostNic01(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )


class TestHostNetworkApiHostNic02(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )


class TestHostNetworkApiHostNic03(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )


class TestHostNetworkApiHostNic04(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[2], **network_host_api_dict
        )


class TestHostNetworkApiHostNic05(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[2], **network_host_api_dict
        )


class TestHostNetworkApiHostNic06(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[2], **network_host_api_dict
        )


class TestHostNetworkApiHostNic07(helper.TestHostNetworkApiTestCaseBase):
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
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net,
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )


class TestHostNetworkApiHostNic08(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True
    net_1 = conf.NIC_NETS[8][0]
    net_2 = conf.NIC_NETS[8][1]

    @classmethod
    def setup_class(cls):
        """
        Attach Non-VM network with 5000 MTU size to host NIC
        """
        network_host_api_dict = {
            "network": cls.net_1
        }
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )

    @polarion("RHEVM3-10451")
    def test_network_mtu_on_host_nic(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2
        }
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], positive=False, **network_host_api_dict
        )


class TestHostNetworkApiHostNic09(helper.TestHostNetworkApiTestCaseBase):
    """
    Remove network from host NIC
    """
    __test__ = True
    net = conf.NIC_NETS[9][0]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster
        """
        network_host_api_dict = {
            "network": cls.net
        }
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )

    @polarion("RHEVM3-10452")
    def test_network_remove_from_host_nic(self):
        """
        Remove network from host NIC
        """
        if not hl_host_network.remove_networks_from_host(
            conf.HOST_0_NAME, [conf.NIC_NETS[9][0]], conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHostNic10(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach networks to host NICs
    2.Update the network to have IP (netmask)
    3.Update the network to have IP (prefix)
    """
    __test__ = True
    ip_netmask = conf.IPS[8]
    ip_prefix = conf.IPS[9]
    net_1 = conf.NIC_NETS[10][0]
    net_2 = conf.NIC_NETS[10][1]

    @classmethod
    def setup_class(cls):
        """
        Attach networks to host NICs
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_1,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": cls.net_2,
                    "nic": conf.HOST_0_NICS[2]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

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
        if not hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1],
            **network_host_nic_1_api_dict
        ):
            raise conf.NET_EXCEPTION()

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
        if not hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[2],
            **network_host_nic_1_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHostNic11(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network to BOND
    """
    __test__ = True
    bond = "bond11"
    dummys = conf.DUMMYS[:2]
    net = conf.NIC_NETS[11][0]

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond,
                    "slaves": cls.dummys
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10454")
    def test_network_on_bond_host_nic(self):
        """
        Attach network on BOND
        """
        network_host_api_dict = {
            "network": self.net
        }
        helper.attach_network_attachment(
            nic=self.bond, **network_host_api_dict
        )


class TestHostNetworkApiHostNic12(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach 3 networks to BOND
    2.Delete 2 networks from the BOND
    """
    __test__ = True
    bond = "bond12"
    dummys = conf.DUMMYS[:2]
    net_1 = conf.NIC_NETS[12][0]
    net_2 = conf.NIC_NETS[12][1]
    net_3 = conf.NIC_NETS[12][2]
    net_list_to_remove = [net_2, net_3]

    @classmethod
    def setup_class(cls):
        """
        1.Create BOND
        2.Attach 3 networks to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond,
                    "slaves": cls.dummys
                },
                "2": {
                    "nic": cls.bond,
                    "network": cls.net_1
                },
                "3": {
                    "nic": cls.bond,
                    "network": cls.net_2
                },
                "4": {
                    "nic": cls.bond,
                    "network": cls.net_3
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10455")
    def test_remove_networks_from_bond_host_nic(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host NIC
        """
        for net in self.net_list_to_remove:
            if not hl_host_network.remove_networks_from_host(
                host_name=conf.HOST_0_NAME, networks=[net]
            ):
                raise conf.NET_EXCEPTION()


class TestHostNetworkApiHostNic13(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
        )


class TestHostNetworkApiHostNic14(helper.TestHostNetworkApiTestCaseBase):
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[1], **network_host_api_dict
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
        helper.attach_network_attachment(
            nic=conf.HOST_0_NICS[2], **network_host_api_dict
        )


class TestHostNetworkApiHostNic15(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True
    bond = "bond15"
    dummys = conf.DUMMYS[:2]
    net = conf.NIC_NETS[15][0]

    @classmethod
    def setup_class(cls):
        sn_dict = {
            "add": {
                "1": {
                    "nic": cls.bond,
                    "slaves": cls.dummys
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-11878")
    def test_network_custom_properties_on_bond_host_nic(self):
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
            "network": self.net,
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            nic=self.bond, **network_host_api_dict
        )
