#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via host NIC href
"""

import config as c
import logging
import helper
from art.unittest_lib import attr
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.host_network_api as hna

logger = logging.getLogger("Host_Network_API_Host_NIC_Cases")


@attr(tier=1)
class TestHostNetworkApiHostNic01(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network to host NIC
    """
    __test__ = True

    def test_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[1][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[1][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic02(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True

    def test_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[2][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[2][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic03(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    def test_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[3][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[3][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic04(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP to host NIC
    """
    __test__ = True

    def test_ip_network_on_host_nic(self):
        """
        Attach network with IP to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[4][0],
            "ip": c.BASIC_IP_DICT
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[4][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic05(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP to host NIC
    """
    __test__ = True

    def test_ip_vlan_network_on_host_nic(self):
        """
        Attach VLAN network with IP to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[5][0],
            "ip": c.BASIC_IP_DICT
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[5][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic06(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP to host NIC
    """
    __test__ = True

    def test_ip_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network with IP to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[6][0],
            "ip": c.BASIC_IP_DICT
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[6][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic07(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True

    def test_network_custom_properties_on_host_nic(self):
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
            "network": c.NIC_NETS[7][0],
            "properties": properties_dict
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[7][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic08(hna.TestHostNetworkApiTestCaseBase):
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
            "network": c.NIC_NETS[8][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[8][0], hna.c.HOST_NICS[1]
        )

    def test_network_mtu_on_host_nic(self):
        """
        Negative: Try to attach VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[8][1]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[8][1], hna.c.HOST_NICS[1], False
        )


@attr(tier=1)
class TestHostNetworkApiHostNic09(hna.TestHostNetworkApiTestCaseBase):
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
            "network": c.NIC_NETS[9][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[9][0], hna.c.HOST_NICS[1]
        )

    def test_network_remove_from_host_nic(self):
        """
        Remove network from host NIC
        """
        logger.info(
            "Removing net_case10 from %s NIC of %s",
            hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.remove_networks_from_host(
            c.HOST_0, [c.NIC_NETS[9][0]], hna.c.HOST_NICS[1]
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove net_case9 from %s of %s" % (
                    hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiHostNic10(hna.TestHostNetworkApiTestCaseBase):
    """
    1.Attach network to host NIC
    2.Update the network to have IP
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[10][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[10][0], hna.c.HOST_NICS[1]
        )

    def test_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[10][0],
            "ip": c.BASIC_IP_DICT
        }
        logger.info(
            "Updating net_case10 network to have IP on %s NIC of %s",
            hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.update_network_on_host(
            c.HOST_0, c.NIC_NETS[10][0], hna.c.HOST_NICS[1],
            **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update net_case10 network with IP on %s of %s" %
                (hna.c.HOST_NICS[1], c.HOST_0)
            )


@attr(tier=1)
class TestHostNetworkApiHostNic11(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network to BOND
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
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        logger.info("Creating bond11 on %s", c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION("Failed to create bond11 on %s" % c.HOST_0)

    def test_network_on_bond_host_nic(self):
        """
        Attach network on BOND
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[11][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[11][0], "bond11"
        )


@attr(tier=1)
class TestHostNetworkApiHostNic12(hna.TestHostNetworkApiTestCaseBase):
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
                    "slaves": [hna.c.HOST_NICS[2], hna.c.HOST_NICS[3]]
                },
                "2": {
                    "nic": "bond12",
                    "network": c.NIC_NETS[12][0]
                },
                "3": {
                    "nic": "bond12",
                    "network": c.NIC_NETS[12][1]
                },
                "4": {
                    "nic": "bond12",
                    "network": c.NIC_NETS[12][2]
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

    def test_remove_networks_from_bond_host_nic(self):
        """
        Remove 2 networks (VLAN and Non-VM) from host NIC
        """
        for i in range(1, 3):
            logger.info(
                "Removing %s from bond12 of %s", c.NIC_NETS[12][i], c.HOST_0)
            if not hl_host_network.remove_networks_from_host(
                c.HOST_0, [c.NIC_NETS[12][i]]
            ):
                raise c.NET_EXCEPTION(
                    "Failed to remove %s from bond12 of %s" % (
                        (c.NIC_NETS[12][i], c.HOST_0)
                    )
                )


@attr(tier=1)
class TestHostNetworkApiHostNic13(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True

    def test_non_vm_vlan_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[13][0]
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[13][0], hna.c.HOST_NICS[1]
        )


@attr(tier=1)
class TestHostNetworkApiHostNic14(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP to host NIC
    """
    __test__ = True

    def test_non_vm_vlan_ip_network_on_host_nic(self):
        """
        Attach Non-VM VLAN network with IP to host NIC
        """
        network_host_api_dict = {
            "network": c.NIC_NETS[14][0],
            "ip": c.BASIC_IP_DICT
        }
        helper.attach_network_attachment(
            network_host_api_dict, c.NIC_NETS[14][0], hna.c.HOST_NICS[1]
        )
