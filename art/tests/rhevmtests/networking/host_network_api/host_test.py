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
    logger.info(
        "Add %s to %s/%s", conf.HOST_DICT, conf.DC_NAME_1, conf.CLUSTER_NAME_1
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.HOST_DICT, dc=conf.DC_NAME_1,
        cluster=conf.CLUSTER_NAME_1
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

    @polarion("RHEVM3-10456")
    def test_network_on_host(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[1][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[1][0]
        )


class TestHostNetworkApiHost02(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10458")
    def test_vlan_network_on_host(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[2][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[2][0]
        )


class TestHostNetworkApiHost03(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10457")
    def test_non_vm_network_on_host(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[3][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[3][0]
        )


class TestHostNetworkApiHost04(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10460")
    def test_ip_netmask_network_on_host(self):
        """
        Attach network with IP to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[4][0],
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[4][0]
        )

    @polarion("RHEVM3-10460")
    def test_ip_prefix_network_on_host(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[4][1],
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[4][1]
        )


class TestHostNetworkApiHost05(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10461")
    def test_ip_netmask_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[5][0],
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[5][0]
        )

    @polarion("RHEVM3-10461")
    def test_ip_prefix_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[5][1],
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[5][1]
        )


class TestHostNetworkApiHost06(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10462")
    def test_ip_netmask_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[6][0],
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[6][0]
        )

    @polarion("RHEVM3-10462")
    def test_ip_prefix_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[6][1],
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[6][1]
        )


class TestHostNetworkApiHost07(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True

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
            "network": conf.HOST_NETS[7][0],
            "nic": conf.HOST_0_NICS[1],
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[7][0]
        )


class TestHostNetworkApiHost08(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach Non-VM network with 5000 MTU size to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[8][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[8][0]
        )

    @polarion("RHEVM3-10465")
    def test_network_mtu_on_host(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[8][1],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[8][1], positive=False
        )


class TestHostNetworkApiHost09(helper.TestHostNetworkApiTestCaseBase):
    """
    Remove network from host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[9][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[9][0]
        )

    @polarion("RHEVM3-10466")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        logger.info(
            "Removing net_case9 from %s NIC of %s",
            conf.HOST_0_NICS[1], conf.HOST_0_NAME
        )
        if not hl_host_network.remove_networks_from_host(
            conf.HOST_0_NAME, [conf.HOST_NETS[9][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Failed to remove net_case9 from %s of %s" % (
                    conf.HOST_0_NICS[1], conf.HOST_0_NAME
                )
            )


class TestHostNetworkApiHost10(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach networks to host NICs
    2.Update the network to have IP (netmask)
    3.Update the network to have IP (prefix)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach networks to host NICs
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[10][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[10][0]
        )
        network_host_api_dict = {
            "network": conf.HOST_NETS[10][1],
            "nic": conf.HOST_0_NICS[2]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[10][1]
        )

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[10][0],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        logger.info(
            "Updating %s network to have IP on %s NIC of %s",
            conf.HOST_NETS[10][0], conf.HOST_0_NICS[1], conf.HOST_0_NAME
        )
        if not hl_host_network.update_network_on_host(
            conf.HOST_0_NAME, conf.HOST_NETS[10][0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update %s network with IP on %s of %s" %
                (conf.HOST_NETS[10][0], conf.HOST_0_NICS[1], conf.HOST_0_NAME)
            )

    @polarion("RHEVM3-10467")
    def test_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[10][1],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        logger.info(
            "Updating %s network to have IP on %s NIC of %s",
            conf.HOST_NETS[10][1], conf.HOST_0_NICS[2], conf.HOST_0_NAME
        )
        if not hl_host_network.update_network_on_host(
            conf.HOST_0_NAME, conf.HOST_NETS[10][1], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update %s network with IP on %s of %s" %
                (conf.HOST_NETS[10][1], conf.HOST_0_NICS[2], conf.HOST_0_NAME)
            )


class TestHostNetworkApiHost11(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND
    2.Attach network to BOND
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond11",
                    "slaves": conf.DUMMYS[:2]
                }
            }
        }
        logger.info("Creating bond11 on %s", conf.HOST_0_NAME)
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond11 on %s" % conf.HOST_0_NAME
            )

    @polarion("RHEVM3-10468")
    def test_attach_network_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[11][0],
            "nic": "bond11"
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[11][0]
        )


class TestHostNetworkApiHost12(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach 3 networks to BOND
    2.Delete 2 networks from the BOND
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1.Create BOND
        2.Attach 3 networks to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond12",
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": "bond12",
                    "network": conf.HOST_NETS[12][0]
                },
                "3": {
                    "nic": "bond12",
                    "network": conf.HOST_NETS[12][1]
                },
                "4": {
                    "nic": "bond12",
                    "network": conf.HOST_NETS[12][2]
                }
            }
        }
        logger.info("Creating bond12 with 3 networks on %s", conf.HOST_0_NAME)
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond12 with 3 networks on %s" %
                conf.HOST_0_NAME
            )

    @polarion("RHEVM3-10469")
    def test_remove_networks_from_bond_host(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host
        """
        for i in range(1, 3):
            logger.info(
                "Removing %s from bond12 of %s",
                conf.HOST_NETS[12][i], conf.HOST_0_NAME
            )
            if not hl_host_network.remove_networks_from_host(
                conf.HOST_0_NAME, [conf.HOST_NETS[12][i]]
            ):
                raise conf.NET_EXCEPTION(
                    "Failed to remove %s from bond12 of %s" % (
                        (conf.HOST_NETS[12][i], conf.HOST_0_NAME)
                    )
                )


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
        logger.info(
            "Create and attach %s to %s/%s",
            cls.unmamanged_net, conf.DC_NAME_1, conf.CLUSTER_NAME_1
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_1, cluster=conf.CLUSTER_NAME_1,
            network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add networks to %s/%s" %
                (conf.DC_NAME_1, conf.CLUSTER_NAME_1)
            )
        network_host_api_dict = {
            "network": cls.unmamanged_net,
            "nic": conf.HOST_0_NICS[1]
        }
        logger.info("Attach %s to %s", cls.unmamanged_net, conf.HOST_0_NAME)
        helper.attach_network_attachment(
            network_host_api_dict, cls.unmamanged_net
        )
        if not ll_networks.removeNetwork(
            True, cls.unmamanged_net, conf.DC_NAME_1
        ):
            raise conf.NET_EXCEPTION(
                "Failed to delete %s from %s" %
                (cls.unmamanged_net, conf.DC_NAME_1)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            conf.HOST_0_NAME, [cls.unmamanged_net]
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
        logger.info(
            "Removing %s from %s", self.unmamanged_net, conf.HOST_0_NAME
        )
        if not ll_host_network.remove_unmanaged_networks(
            conf.HOST_0_NAME, networks=[self.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s from %s" %
                (self.unmamanged_net, conf.HOST_0_NAME)
            )


class TestHostNetworkApiHost14(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10459")
    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[14][0],
            "nic": conf.HOST_0_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[14][0]
        )


class TestHostNetworkApiHost15(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[15][0],
            "nic": conf.HOST_0_NICS[1],
            "ip": conf.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[15][0]
        )

    @polarion("RHEVM3-10463")
    def test_non_vm_vlan_ip_prefix_on_host(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": conf.HOST_NETS[15][1],
            "nic": conf.HOST_0_NICS[2],
            "ip": conf.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[15][1]
        )


class TestHostNetworkApiHost16(helper.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host (BOND)
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_host16"

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
        logger.info(
            "Create and attach %s to %s/%s",
            cls.unmamanged_net, conf.DC_NAME_1, conf.CLUSTER_NAME_1
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_1, cluster=conf.CLUSTER_NAME_1,
            network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add network to %s/%s" %
                (conf.DC_NAME_1, conf.CLUSTER_NAME_1)
            )
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond16",
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": "bond16",
                    "network": cls.unmamanged_net
                }
            }
        }
        logger.info(
            "Create bond16 with %s on %s", conf.HOST_0_NAME, cls.unmamanged_net
        )
        if not hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to create bond16 with %s on %s" %
                (cls.unmamanged_net, conf.HOST_0_NAME)
            )
        if not ll_networks.removeNetwork(
            True, cls.unmamanged_net, conf.DC_NAME_1
        ):
            raise conf.NET_EXCEPTION(
                "Failed to delete %s from %s" %
                (cls.unmamanged_net, conf.DC_NAME_1)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            conf.HOST_0_NAME, [cls.unmamanged_net]
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
        logger.info(
            "Removing %s from %s", self.unmamanged_net, conf.HOST_0_NAME
        )
        if not ll_host_network.remove_unmanaged_networks(
            conf.HOST_0_NAME, networks=[self.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s from %s" %
                (self.unmamanged_net, conf.HOST_0_NAME)
            )


class TestHostNetworkApiHost17(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond17",
                    "slaves": conf.DUMMYS[:2]
                }
            }
        }
        if not hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to create bond17 on %s" % conf.HOST_0_NAME
            )

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
            "network": conf.HOST_NETS[17][0],
            "nic": "bond17",
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            network_host_api_dict, conf.HOST_NETS[17][0]
        )


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
        if not hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s on %s" %
                (cls.net_case_pre_vm, cls.net_case_pre_vlan, conf.HOST_0_NAME)
            )

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vlan,
            "nic": conf.HOST_0_NICS[1],
        }
        helper.attach_network_attachment(
            network_host_api_dict, self.net_case_vlan
        )

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "network": self.net_case_vm,
            "nic": conf.HOST_0_NICS[2],
        }
        helper.attach_network_attachment(
            network_host_api_dict, self.net_case_vm
        )
