#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host href
"""

import config as c
import logging
import helper
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.host_network_api as hna

logger = logging.getLogger("Host_Network_API_Host_Cases")


@attr(tier=1)
@polarion("RHEVM3-10456")
class TestHostNetworkApiHost01(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network to host NIC
    """
    __test__ = True

    def test_network_on_host(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[1][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[1][0]
        )


@attr(tier=1)
@polarion("RHEVM3-10458")
class TestHostNetworkApiHost02(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True

    def test_vlan_network_on_host(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[2][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[2][0]
        )


@attr(tier=1)
@polarion("RHEVM3-10457")
class TestHostNetworkApiHost03(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    def test_non_vm_network_on_host(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[3][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[3][0]
        )


@attr(tier=1)
@polarion("RHEVM3-10460")
class TestHostNetworkApiHost04(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_netmask_network_on_host(self):
        """
        Attach network with IP to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[4][0],
            "nic": hna.c.HOST_NICS[1],
            "ip": c.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[4][0]
        )

    def test_ip_prefix_network_on_host(self):
        """
        Attach network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[4][1],
            "nic": hna.c.HOST_NICS[2],
            "ip": c.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[4][1]
        )


@attr(tier=1)
@polarion("RHEVM3-10461")
class TestHostNetworkApiHost05(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_netmask_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[5][0],
            "nic": hna.c.HOST_NICS[1],
            "ip": c.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[5][0]
        )

    def test_ip_prefix_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[5][1],
            "nic": hna.c.HOST_NICS[2],
            "ip": c.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[5][1]
        )


@attr(tier=1)
@polarion("RHEVM3-10462")
class TestHostNetworkApiHost06(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_netmask_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[6][0],
            "nic": hna.c.HOST_NICS[1],
            "ip": c.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[6][0]
        )

    def test_ip_prefix_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[6][1],
            "nic": hna.c.HOST_NICS[2],
            "ip": c.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[6][1]
        )


@attr(tier=1)
@polarion("RHEVM3-10464")
class TestHostNetworkApiHost07(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True

    def test_network_custom_properties_on_host(self):
        """
        Attach network with custom properties to host NIC
        """
        properties_dict = {
            "bridge_opts": c.PRIORITY,
            "ethtool_opts": c.TX_CHECKSUM.format(
                nic=hna.c.HOST_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": c.HOST_NETS[7][0],
            "nic": hna.c.HOST_NICS[1],
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[7][0]
        )


@attr(tier=1)
@polarion("RHEVM3-10465")
class TestHostNetworkApiHost08(hna.TestHostNetworkApiTestCaseBase):
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
            "network": c.HOST_NETS[8][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[8][0]
        )

    def test_network_mtu_on_host(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[8][1],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[8][1], positive=False
        )


@attr(tier=1)
@polarion("RHEVM3-10466")
class TestHostNetworkApiHost09(hna.TestHostNetworkApiTestCaseBase):
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
            "network": c.HOST_NETS[9][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[9][0]
        )

    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        logger.info(
            "Removing net_case9 from %s NIC of %s",
            hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.remove_networks_from_host(
            c.HOST_0, [c.HOST_NETS[9][0]]
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove net_case9 from %s of %s" % (
                    hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10467")
class TestHostNetworkApiHost10(hna.TestHostNetworkApiTestCaseBase):
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
            "network": c.HOST_NETS[10][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[10][0]
        )
        network_host_api_dict = {
            "network": c.HOST_NETS[10][1],
            "nic": hna.c.HOST_NICS[2]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[10][1]
        )

    def test_update_network_with_ip_netmask_host_nic(self):
        """
        Update the network to have IP (netmask)
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[10][0],
            "ip": c.BASIC_IP_DICT_NETMASK
        }
        logger.info(
            "Updating %s network to have IP on %s NIC of %s",
            c.HOST_NETS[10][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.update_network_on_host(
            c.HOST_0, c.HOST_NETS[10][0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update %s network with IP on %s of %s" %
                (c.HOST_NETS[10][0], hna.c.HOST_NICS[1], c.HOST_0)
            )

    def test_update_network_with_ip_prefix_host_nic(self):
        """
        Update the network to have IP (prefix)
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[10][1],
            "ip": c.BASIC_IP_DICT_PREFIX
        }
        logger.info(
            "Updating %s network to have IP on %s NIC of %s",
            c.HOST_NETS[10][1], hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.update_network_on_host(
            c.HOST_0, c.HOST_NETS[10][1], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update %s network with IP on %s of %s" %
                (c.HOST_NETS[10][1], hna.c.HOST_NICS[2], c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-10468")
class TestHostNetworkApiHost11(hna.TestHostNetworkApiTestCaseBase):
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
                    "slaves": [hna.c.HOST_NICS[2], hna.c.HOST_NICS[3]]
                }
            }
        }
        logger.info("Creating bond11 on %s", c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to create bond11 on %s" % c.HOST_0
            )

    def test_attach_network_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[11][0],
            "nic": "bond11"
        }
        helper.attach_network_attachment(network_host_api_dict, "bond11")


@attr(tier=1)
@polarion("RHEVM3-10469")
class TestHostNetworkApiHost12(hna.TestHostNetworkApiTestCaseBase):
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
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "2": {
                    "nic": "bond12",
                    "network": c.HOST_NETS[12][0]
                },
                "3": {
                    "nic": "bond12",
                    "network": c.HOST_NETS[12][1]
                },
                "4": {
                    "nic": "bond12",
                    "network": c.HOST_NETS[12][2]
                }
            }
        }
        logger.info("Creating bond12 with 3 networks on %s", c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to create bond12 with 3 networks on %s" % c.HOST_0
            )

    def test_remove_networks_from_bond_host(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host
        """
        for i in range(1, 3):
            logger.info(
                "Removing %s from bond12 of %s",
                c.HOST_NETS[12][i], c.HOST_0
            )
            if not hl_host_network.remove_networks_from_host(
                c.HOST_0, [c.HOST_NETS[12][i]]
            ):
                raise c.NET_EXCEPTION(
                    "Failed to remove %s from bond12 of %s" % (
                        (c.HOST_NETS[12][i], c.HOST_0)
                    )
                )


@attr(tier=1)
@polarion("RHEVM3-12165")
class TestHostNetworkApiHost13(hna.TestHostNetworkApiTestCaseBase):
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
            cls.unmamanged_net, c.DC_NAME, c.CLUSTER_NAME
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=c.DC_NAME, cluster=c.CLUSTER, network_dict=network_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to add networks to %s/%s" % (c.DC_NAME, c.CLUSTER)
            )
        network_host_api_dict = {
            "network": cls.unmamanged_net,
            "nic": hna.c.HOST_NICS[1]
        }
        logger.info("Attach %s to %s", cls.unmamanged_net, c.HOST_0)
        helper.attach_network_attachment(
            network_host_api_dict, cls.unmamanged_net
        )
        if not hl_networks.removeNetwork(True, cls.unmamanged_net, c.DC_NAME):
            raise c.NET_EXCEPTION(
                "Failed to delete %s from %s" % (cls.unmamanged_net, c.DC_NAME)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            c.HOST_0, [cls.unmamanged_net]
        ):
            raise c.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        logger.info("Removing %s from %s", self.unmamanged_net, c.HOST_0)
        if not ll_host_network.remove_unmanaged_networks(
            c.HOST_0, networks=[self.unmamanged_net]
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s" % (self.unmamanged_net, c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-10459")
class TestHostNetworkApiHost14(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True

    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[14][0],
            "nic": hna.c.HOST_NICS[1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[14][0]
        )


@attr(tier=1)
@polarion("RHEVM3-10463")
class TestHostNetworkApiHost15(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_non_vm_vlan_ip_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[15][0],
            "nic": hna.c.HOST_NICS[1],
            "ip": c.BASIC_IP_DICT_NETMASK
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[15][0]
        )

    def test_non_vm_vlan_ip_prefix_on_host(self):
        """
        Attach Non-VM VLAN network with IP (prefix) to host NIC
        """
        network_host_api_dict = {
            "network": c.HOST_NETS[15][1],
            "nic": hna.c.HOST_NICS[2],
            "ip": c.BASIC_IP_DICT_PREFIX
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[15][1]
        )


@attr(tier=1)
@polarion("RHEVM3-12166")
class TestHostNetworkApiHost16(hna.TestHostNetworkApiTestCaseBase):
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
            cls.unmamanged_net, c.DC_NAME, c.CLUSTER_NAME
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=c.DC_NAME, cluster=c.CLUSTER, network_dict=network_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to add network to %s/%s" % (c.DC_NAME, c.CLUSTER)
            )
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond16",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "2": {
                    "nic": "bond16",
                    "network": cls.unmamanged_net
                }
            }
        }
        logger.info(
            "Create bond16 with %s on %s", c.HOST_0, cls.unmamanged_net
        )
        if not hl_host_network.setup_networks(c.HOST_0, **sn_dict):
            raise c.NET_EXCEPTION(
                "Failed to create bond16 with %s on %s" %
                (cls.unmamanged_net, c.HOST_0)
            )
        if not hl_networks.removeNetwork(True, cls.unmamanged_net, c.DC_NAME):
            raise c.NET_EXCEPTION(
                "Failed to delete %s from %s" % (cls.unmamanged_net, c.DC_NAME)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            c.HOST_0, [cls.unmamanged_net]
        ):
            raise c.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        logger.info("Removing %s from %s", self.unmamanged_net, c.HOST_0)
        if not ll_host_network.remove_unmanaged_networks(
            c.HOST_0, networks=[self.unmamanged_net]
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s" % (self.unmamanged_net, c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-11879")
class TestHostNetworkApiHost17(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond17",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        if not hl_host_network.setup_networks(c.HOST_0, **sn_dict):
            raise c.NET_EXCEPTION(
                "Failed to create bond17 on %s" % c.HOST_0
            )

    def test_network_custom_properties_on_bond_host(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": c.PRIORITY,
            "ethtool_opts": c.TX_CHECKSUM.format(
                nic=hna.c.HOST_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "network": c.HOST_NETS[17][0],
            "nic": "bond17",
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.HOST_NETS[17][0]
        )
