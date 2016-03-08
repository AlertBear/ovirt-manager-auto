#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host href
"""

import helper
import logging
import config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Host_Cases")


def setup_module():
    """
    Add networks
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.HOST_DICT, dc=conf.DC_0,
        cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks
    """
    network_helper.remove_networks_from_setup()


class TestHostNetworkApiHost01(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost02(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost03(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost04(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10460")
    def test_ip_prefix_network_on_host(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost05(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10461")
    def test_ip_prefix_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost06(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10462")
    def test_ip_prefix_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost07(helper.TestHostNetworkApiTestCaseBase):
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
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": self.net,
            "nic": conf.HOST_0_NICS[1],
            "properties": properties_dict
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost08(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True
    net_1 = conf.HOST_NETS[8][0]
    net_2 = conf.HOST_NETS[8][1]

    @classmethod
    def setup_class(cls):
        """
        Attach Non-VM network with 5000 MTU size to host NIC
        """
        network_host_api_dict = {
            "network": cls.net_1,
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10465")
    def test_network_mtu_on_host(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            positive=False, **network_host_api_dict
        )


class TestHostNetworkApiHost09(helper.TestHostNetworkApiTestCaseBase):
    """
    Remove network from host NIC
    """
    __test__ = True
    net = conf.HOST_NETS[9][0]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster
        """
        network_host_api_dict = {
            "network": cls.net,
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10466")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        if not hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHost10(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach networks to host NICs
    2.Update the network to have IP (netmask)
    3.Update the network to have IP (prefix)
    """
    __test__ = True
    ip_netmask = conf.IPS[18]
    ip_prefix = conf.IPS[19]
    net_1 = conf.HOST_NETS[10][0]
    net_2 = conf.HOST_NETS[10][1]

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

        if not hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

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
        if not hl_host_network.update_network_on_host(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHost11(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND
    2.Attach network to BOND
    """
    __test__ = True
    bond = "bond11"
    dummys = conf.DUMMYS[:2]
    net = conf.HOST_NETS[11][0]

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

    @polarion("RHEVM3-10468")
    def test_attach_network_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "network": self.net,
            "nic": self.bond
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost12(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach 3 networks to BOND
    2.Delete 2 networks from the BOND
    """
    __test__ = True
    bond = "bond12"
    dummys = conf.DUMMYS[:2]
    net_1 = conf.HOST_NETS[12][0]
    net_2 = conf.HOST_NETS[12][1]
    net_3 = conf.HOST_NETS[12][2]
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

    @polarion("RHEVM3-10469")
    def test_remove_networks_from_bond_host(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host
        """
        for net in self.net_list_to_remove:
            if not hl_host_network.remove_networks_from_host(
                host_name=conf.HOST_0_NAME, networks=[net]
            ):
                raise conf.NET_EXCEPTION()


class TestHostNetworkApiHost13(helper.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_net_13"

    @classmethod
    def setup_class(cls):
        """
        Attach network to host NIC
        """
        network_dict = {
            cls.unmamanged_net: {
                "required": "false"
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0, network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION()

        network_host_api_dict = {
            "network": cls.unmamanged_net,
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)
        if not ll_networks.removeNetwork(
            positive=True, network=cls.unmamanged_net, data_center=conf.DC_0
        ):
            raise conf.NET_EXCEPTION()

        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[cls.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    @polarion("RHEVM3-12165")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        if not ll_host_network.remove_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHost14(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost15(helper.TestHostNetworkApiTestCaseBase):
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
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(**network_host_api_dict)

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_prefix_on_host(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        network_host_api_dict = {
            "network": self.net_2,
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost16(helper.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host (BOND)
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_host16"
    bond = "bond16"
    dummys = conf.DUMMYS[:2]

    @classmethod
    def setup_class(cls):
        """
        Attach network to host NIC
        """
        network_dict = {
            cls.unmamanged_net: {
                "required": "false"
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0, network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION()

        sn_dict = {
            "add": {
                "1": {
                    "nic": cls.bond,
                    "slaves": cls.dummys
                },
                "2": {
                    "nic": cls.bond,
                    "network": cls.unmamanged_net
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.removeNetwork(
            positive=True, network=cls.unmamanged_net, data_center=conf.DC_0
        ):
            raise conf.NET_EXCEPTION()

        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[cls.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    @polarion("RHEVM3-12166")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        if not ll_host_network.remove_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiHost17(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True
    bond = "bond17"
    dummys = conf.DUMMYS[:2]
    net = conf.HOST_NETS[17][0]

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
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

    @polarion("RHEVM3-11879")
    def test_network_custom_properties_on_bond_host(self):
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
            "nic": self.bond,
            "properties": properties_dict
        }
        helper.attach_network_attachment(**network_host_api_dict)


class TestHostNetworkApiHost18(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VM network to host NIC that has VLAN network on it
    Attach VLAN network to host NIC that has VM network on it
    """
    __test__ = True
    net_case_pre_vm = conf.HOST_NETS[18][0]
    net_case_pre_vlan = conf.HOST_NETS[18][1]
    net_case_vlan = conf.HOST_NETS[18][2]
    net_case_vm = conf.HOST_NETS[18][3]

    @classmethod
    def setup_class(cls):
        """
        Attach VM and VLAN networks to host NICs
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.net_case_pre_vm
                },
                "2": {
                    "nic": conf.HOST_0_NICS[2],
                    "network": cls.net_case_pre_vlan
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vlan,
            "nic": conf.HOST_0_NICS[1],
        }
        helper.attach_network_attachment(**network_host_api_dict)

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vm,
            "nic": conf.HOST_0_NICS[2],
        }
        helper.attach_network_attachment(**network_host_api_dict)
