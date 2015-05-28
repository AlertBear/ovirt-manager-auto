#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
"""

import config as c
import logging
from art.unittest_lib import attr
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.host_network_api as hna

logger = logging.getLogger("Host_Network_API_SN_Cases")


@attr(tier=1)
class TestHostNetworkApiSetupNetworks01(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network to host NIC
    """
    __test__ = True

    def test_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[1][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[1][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[1][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks02(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True

    def test_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[2][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[2][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[2][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks03(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    def test_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[3][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[3][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[3][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks04(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP to host NIC
    """
    __test__ = True

    def test_ip_network_on_host(self):
        """
        Attach network with IP to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[4][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[4][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[4][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks05(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP to host NIC
    """
    __test__ = True

    def test_ip_vlan_network_on_host(self):
        """
        Attach VLAN network with IP to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[5][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[5][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[5][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks06(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP to host NIC
    """
    __test__ = True

    def test_ip_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[6][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[6][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[6][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks07(hna.TestHostNetworkApiTestCaseBase):
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
            "add": {
                "1": {
                    "network": c.NETWORKS[7][0],
                    "nic": hna.c.HOST_NICS[1],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[7][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[7][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks08(hna.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True

    def test_network_mtu_on_host(self):
        """
        Attach Non-VM network with 5000 MTU size to host NIC and try to attach
        VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[8][0],
                    "nic": hna.c.HOST_NICS[1]
                },
                "2": {
                    "network": c.NETWORKS[8][1],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s(MTU5000) and %s(MTU9000) to %s on %s",
            c.NETWORKS[8][0], c.NETWORKS[8][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "%s and %s is attached to %s on %s but shouldn't" % (
                    c.NETWORKS[8][0], c.NETWORKS[8][1], hna.c.HOST_NICS[1],
                    c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks09(hna.TestHostNetworkApiTestCaseBase):
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
            "add": {
                "1": {
                    "network": c.NETWORKS[9][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[9][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[9][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )

    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        network_host_api_dict = {
            "remove": {
                "networks": [c.NETWORKS[9][0]]
                }
            }
        logger.info(
            "Removing %s from %s on %s",
            c.NETWORKS[9][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s on %s" % (
                    c.NETWORKS[9][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks10(hna.TestHostNetworkApiTestCaseBase):
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
            "add": {
                "1": {
                    "network": c.NETWORKS[10][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.NETWORKS[10][0], hna.c.HOST_NICS[1], c.HOST_0)
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.NETWORKS[10][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )

    def test_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": c.NETWORKS[10][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT
                }
            }
        }
        logger.info(
            "Updating %s to have IP on %s of %s",
            c.NETWORKS[10][0], hna.c.HOST_NICS[1], c.HOST_0)
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update %s to have IP on %s of %s" % (
                    c.NETWORKS[10][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks11(hna.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND
    2.Attach network to BOND
    3.Remove networks from BOND
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
        logger.info("Creating bond11 on %s", c.HOSTS[0])
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION("Failed to create bond11 on %s" % c.HOSTS[0])

    def test_attach_networks_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.NETWORKS[11][0],
                    "nic": "bond11"
                },
                "2": {
                    "nic": "bond11",
                    "network": c.NETWORKS[11][1]
                },
                "3": {
                    "nic": "bond11",
                    "network": c.NETWORKS[11][2]
                }
            }
        }
        logger.info(
            "Attach %s to bond11 on %s", c.NETWORKS[11][0], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to bond11 on %s" % (
                    c.NETWORKS[11][0], c.HOST_0
                )
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks12(hna.TestHostNetworkApiTestCaseBase):
    """
    1. Create BOND
    2. Add slave to BOND
    3. Remove slaves from BOND
    4. Update BOND mode
    5. Attach network with IP to BOND
    """
    __test__ = True

    def test_01create_bond(self):
        """
        Create BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond12",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        logger.info("Creating bond12 on %s", c.HOSTS[0])
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION("Failed to create bond12 on %s" % c.HOSTS[0])

    def test_02update_bond_add_slave(self):
        """
        Add slave to BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": "bond12",
                    "slaves": [
                        hna.c.HOST_NICS[1],
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update bond12 to have 3 slaves on %s" % c.HOSTS[0]
            )

    def test_03update_bond_remove_slave(self):
        """
        Remove slave from BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": "bond12",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update bond12 to have 2 slaves on %s" % c.HOSTS[0]
            )

    def test_04update_bond_mode(self):
        """
        Update BOND to mode 1
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": "bond12",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ],
                    "mode": "1"
                }
            }
        }
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update bond12 mode to mode 1 on %s" % c.HOSTS[0]
            )

    def test_05update_bond_with_ip(self):
        """
        Attach network with IP to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond12",
                    "network": c.NETWORKS[14][0],
                    "ip": c.BASIC_IP_DICT
                }
            }
        }
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s with IP to bond12 on %s" %
                (c.NETWORKS[14][0], c.HOSTS[0])
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks13(hna.TestHostNetworkApiTestCaseBase):
    """
    Create 3 BONDs
    """
    __test__ = True

    def test_create_bonds(self):
        """
        Create BONDs
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond131",
                    "slaves": ["dummy0", "dummy1"]
                },
                "2": {
                    "nic": "bond132",
                    "slaves": ["dummy2", "dummy3"]
                },
                "3": {
                    "nic": "bond133",
                    "slaves": ["dummy4", "dummy5"]
                }
            }
        }
        logger.info("Creating bond131/2/3 on %s", c.HOSTS[0])
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to create bond131/2/3 on %s" % c.HOSTS[0]
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks14(hna.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with 5 slaves
    """
    __test__ = True

    def test_create_bond_with_5_slaves(self):
        """
        Create BOND with 5 slaves
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond14",
                    "slaves": [
                        "dummy0",
                        "dummy1",
                        "dummy2",
                        "dummy3",
                        "dummy4"
                    ]
                }
            }
        }
        logger.info("Creating bond14 on %s", c.HOSTS[0])
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION("Failed to create bond14 on %s" % c.HOSTS[0])


@attr(tier=1)
class TestHostNetworkApiSetupNetworks15(hna.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND with 3 networks
    2.Remove networks from BOND
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
                    "nic": "bond15",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "2": {
                    "network": c.NETWORKS[15][0],
                    "nic": "bond15"
                },
                "3": {
                    "nic": "bond15",
                    "network": c.NETWORKS[15][1]
                },
                "4": {
                    "nic": "bond15",
                    "network": c.NETWORKS[15][2]
                }
            }
        }
        logger.info("Creating bond15 on %s", c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION("Failed to create bond15 on %s" % c.HOST_0)

    def test_remove_networks_from_bond_host(self):
        """
        Remove network from BOND
        """
        network_host_api_dict = {
            "remove": {
                "networks": [c.NETWORKS[15][1], c.NETWORKS[15][2]]
            }
        }
        logger.info(
            "Removing %s and %s from bond15 on %s",
            c.NETWORKS[15][1], c.NETWORKS[15][2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s and %s from bond15 on %s" % (
                    c.NETWORKS[15][1], c.NETWORKS[15][2], c.HOST_0
                )
            )
