#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
"""

import config as c
import logging
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import rhevmtests.networking.host_network_api as hna

logger = logging.getLogger("Host_Network_API_SN_Cases")


@attr(tier=1)
@polarion("RHEVM3-10470")
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
                    "network": c.SN_NETS[1][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[1][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[1][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10472")
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
                    "network": c.SN_NETS[2][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[2][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[2][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10471")
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
                    "network": c.SN_NETS[3][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[3][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[3][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10474")
class TestHostNetworkApiSetupNetworks04(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_network_on_host(self):
        """
        Attach network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.SN_NETS[4][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": c.SN_NETS[4][1],
                    "nic": hna.c.HOST_NICS[2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            c.SN_NETS[4][0], c.SN_NETS[4][1], hna.c.HOST_NICS[1],
            hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    c.SN_NETS[4][0], c.SN_NETS[4][1], hna.c.HOST_NICS[1],
                    hna.c.HOST_NICS[2], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10475")
class TestHostNetworkApiSetupNetworks05(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.SN_NETS[5][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": c.SN_NETS[5][1],
                    "nic": hna.c.HOST_NICS[2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            c.SN_NETS[5][0], c.SN_NETS[5][1], hna.c.HOST_NICS[1],
            hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    c.SN_NETS[5][0], c.SN_NETS[5][1], hna.c.HOST_NICS[1],
                    hna.c.HOST_NICS[2], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10476")
class TestHostNetworkApiSetupNetworks06(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.SN_NETS[6][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": c.SN_NETS[6][1],
                    "nic": hna.c.HOST_NICS[2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            c.SN_NETS[6][0], c.SN_NETS[6][1], hna.c.HOST_NICS[1],
            hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    c.SN_NETS[6][0], c.SN_NETS[6][1], hna.c.HOST_NICS[1],
                    hna.c.HOST_NICS[2], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10478")
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
                    "network": c.SN_NETS[7][0],
                    "nic": hna.c.HOST_NICS[1],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[7][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[7][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10513")
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
                    "network": c.SN_NETS[8][0],
                    "nic": hna.c.HOST_NICS[1]
                },
                "2": {
                    "network": c.SN_NETS[8][1],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s(MTU5000) and %s(MTU9000) to %s on %s",
            c.SN_NETS[8][0], c.SN_NETS[8][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "%s and %s is attached to %s on %s but shouldn't" % (
                    c.SN_NETS[8][0], c.SN_NETS[8][1], hna.c.HOST_NICS[1],
                    c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10514")
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
                    "network": c.SN_NETS[9][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[9][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[9][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )

    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        network_host_api_dict = {
            "remove": {
                "networks": [c.SN_NETS[9][0]]
                }
            }
        logger.info(
            "Removing %s from %s on %s",
            c.SN_NETS[9][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s on %s" % (
                    c.SN_NETS[9][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10515")
class TestHostNetworkApiSetupNetworks10(hna.TestHostNetworkApiTestCaseBase):
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
            "add": {
                "1": {
                    "network": c.SN_NETS[10][0],
                    "nic": hna.c.HOST_NICS[1]
                },
                "2": {
                    "network": c.SN_NETS[10][1],
                    "nic": hna.c.HOST_NICS[2]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[10][0], hna.c.HOST_NICS[1], c.HOST_0)
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[10][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )

    def test_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP (netmask and prefix)
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": c.SN_NETS[10][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": c.SN_NETS[10][1],
                    "nic": hna.c.HOST_NICS[2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Updating %s and %s to have IP on %s and %s of %s",
            c.SN_NETS[10][0], c.SN_NETS[10][1], hna.c.HOST_NICS[1],
            hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to update %s and %s to have IP on %s and %s of %s" % (
                    c.SN_NETS[10][0], c.SN_NETS[10][0], hna.c.HOST_NICS[1],
                    hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10516")
class TestHostNetworkApiSetupNetworks11(hna.TestHostNetworkApiTestCaseBase):
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
                    "network": c.SN_NETS[11][0],
                    "nic": "bond11"
                },
                "2": {
                    "nic": "bond11",
                    "network": c.SN_NETS[11][1]
                },
                "3": {
                    "nic": "bond11",
                    "network": c.SN_NETS[11][2]
                }
            }
        }
        logger.info(
            "Attach %s to bond11 on %s", c.SN_NETS[11][0], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to bond11 on %s" % (
                    c.SN_NETS[11][0], c.HOST_0
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

    @polarion("RHEVM3-9621")
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

    @polarion("RHEVM3-9622")
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

    @polarion("RHEVM3-10520")
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

    @polarion("RHEVM3-9642")
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

    @polarion("RHEVM3-10521")
    def test_05update_bond_with_ip(self):
        """
        Attach network with IP to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond12",
                    "network": c.SN_NETS[12][0],
                    "ip": c.BASIC_IP_DICT_NETMASK
                }
            }
        }
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s with IP to bond12 on %s" %
                (c.SN_NETS[14][0], c.HOSTS[0])
            )


@attr(tier=1)
@polarion("RHEVM3-10518")
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
@polarion("RHEVM3-10519")
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
@polarion("RHEVM3-10517")
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
                    "network": c.SN_NETS[15][0],
                    "nic": "bond15"
                },
                "3": {
                    "nic": "bond15",
                    "network": c.SN_NETS[15][1]
                },
                "4": {
                    "nic": "bond15",
                    "network": c.SN_NETS[15][2]
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
                "networks": [c.SN_NETS[15][1], c.SN_NETS[15][2]]
            }
        }
        logger.info(
            "Removing %s and %s from bond15 on %s",
            c.SN_NETS[15][1], c.SN_NETS[15][2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to remove %s and %s from bond15 on %s" % (
                    c.SN_NETS[15][1], c.SN_NETS[15][2], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-11432")
class TestHostNetworkApiSetupNetworks16(hna.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host (BOND)
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_sn_16"

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
        if not hl_host_network.clean_host_interfaces(c.HOST_0):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s" % (self.unmamanged_net, c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-12164")
class TestHostNetworkApiSetupNetworks17(hna.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_sn_17"

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
                    "nic": hna.c.HOST_NICS[1],
                    "network": cls.unmamanged_net
                }
            }
        }
        logger.info(
            "Create bond16 with %s on %s", c.HOST_0, cls.unmamanged_net
        )
        if not hl_host_network.setup_networks(c.HOST_0, **sn_dict):
            raise c.NET_EXCEPTION(
                "Failed to attach %s on %s" % (cls.unmamanged_net, c.HOST_0)
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
        if not hl_host_network.clean_host_interfaces(c.HOST_0):
            raise c.NET_EXCEPTION(
                "Failed to remove %s from %s" % (self.unmamanged_net, c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-11880")
class TestHostNetworkApiSetupNetworks18(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True

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
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond18",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "2": {
                    "nic": "bond18",
                    "network": c.SN_NETS[18][0],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to bond18 on %s",
            c.SN_NETS[18][0], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **sn_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to bond18 on %s" % (
                    c.SN_NETS[18][0], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10477")
class TestHostNetworkApiSetupNetworks19(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    def test_ip_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.SN_NETS[19][0],
                    "nic": hna.c.HOST_NICS[1],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": c.SN_NETS[19][1],
                    "nic": hna.c.HOST_NICS[2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            c.SN_NETS[19][0], c.SN_NETS[19][1], hna.c.HOST_NICS[1],
            hna.c.HOST_NICS[2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    c.SN_NETS[19][0], c.SN_NETS[19][1], hna.c.HOST_NICS[1],
                    hna.c.HOST_NICS[2], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10473")
class TestHostNetworkApiSetupNetworks20(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True

    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": c.SN_NETS[20][0],
                    "nic": hna.c.HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            c.SN_NETS[20][0], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    c.SN_NETS[20][0], hna.c.HOST_NICS[1], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-10438")
class TestHostNetworkApiSetupNetworks21(hna.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with network
    """
    __test__ = True

    def test_attach_networks_to_bond(self):
        """
        Create BOND with network
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond21",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "2": {
                    "network": c.SN_NETS[21][0],
                    "nic": "bond21"
                }
            }
        }
        logger.info(
            "Attach %s to bond21 on %s", c.SN_NETS[21][0], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            host_name=c.HOST_0, **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to bond21 on %s" % (
                    c.SN_NETS[21][0], c.HOST_0
                )
            )


@attr(tier=1)
@polarion("RHEVM3-9823")
class TestHostNetworkApiSetupNetworks22(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to host NIC
    """
    __test__ = True

    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[22][0]
                },
                "2": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[22][1]
                },
                "3": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[22][2]
                }
            }
        }
        logger.info(
            "Attaching %s,%s and %s to %s on %s", c.SN_NETS[22][0],
            c.SN_NETS[22][1], c.SN_NETS[22][2], hna.c.HOST_NICS[1], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s, %s and %s to %s on %s" %
                (c.SN_NETS[22][0], c.SN_NETS[22][1], c.SN_NETS[22][2],
                 hna.c.HOST_NICS[1], c.HOST_0)
            )


@attr(tier=1)
@polarion("RHEVM3-9824")
class TestHostNetworkApiSetupNetworks23(hna.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to BOND
    """
    __test__ = True

    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond23",
                    "network": c.SN_NETS[23][0]
                },
                "2": {
                    "nic": "bond23",
                    "network": c.SN_NETS[23][1]
                },
                "3": {
                    "nic": "bond23",
                    "network": c.SN_NETS[23][2]
                },
                "4": {
                    "nic": "bond23",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                }
            }
        }
        logger.info(
            "Attaching %s,%s and %s to bond23 on %s", c.SN_NETS[23][0],
            c.SN_NETS[23][1], c.SN_NETS[23][2], c.HOST_0
        )
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Failed to attach %s, %s and %s to bond23 on %s" %
                (c.SN_NETS[23][0], c.SN_NETS[23][1], c.SN_NETS[23][2],
                 c.HOST_0)
            )


@attr(tier=1)
class TestHostNetworkApiSetupNetworks24(hna.TestHostNetworkApiTestCaseBase):
    """
    Create:
    Attach Non-VM + 2 VLAN networks (IP and custom properties) to NIC1
    Create BOND and attach Non-VM + 1 VLAN network with IP to BOND
    Create empty BOND

    Update:
    Move network from NIC to existing BOND
    Change NIC for existing network
    Add slave to existing BOND and Move network from another BOND to it
    Create new BOND with network attached to it
    Remove network from NIC
    Remove network from BOND
    Remove BOND
    """

    __test__ = True

    @polarion("RHEVM3-9850")
    def test_01_multiple_actions(self):
        """
        Attach Non-VM + 2 VLAN networks (IP and custom properties) to NIC1
        Create BOND and attach Non-VM + 1 VLAN network with IP to BOND
        Create empty BOND
        """
        properties_dict = {
            "bridge_opts": c.PRIORITY,
            "ethtool_opts": c.TX_CHECKSUM.format(
                nic=hna.c.HOST_NICS[2], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[24][0]
                },
                "2": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[24][1],
                },
                "3": {
                    "nic": hna.c.HOST_NICS[1],
                    "network": c.SN_NETS[24][2],
                    "ip": c.BASIC_IP_DICT_PREFIX,
                    "properties": properties_dict
                },
                "4": {
                    "nic": "bond241",
                    "slaves": [
                        hna.c.HOST_NICS[2],
                        hna.c.HOST_NICS[3]
                    ]
                },
                "5": {
                    "nic": "bond241",
                    "network": c.SN_NETS[24][3],
                    "ip": c.BASIC_IP_DICT_NETMASK
                },
                "6": {
                    "nic": "bond241",
                    "network": c.SN_NETS[24][4],
                },
                "7": {
                    "nic": "bond242",
                    "slaves": [
                        "dummy1",
                        "dummy2"
                    ]
                },
                "8": {
                    "nic": "bond243",
                    "slaves": [
                        "dummy5",
                        "dummy6",
                        "dummy7"
                    ]
                },
                "9": {
                    "nic": "bond244",
                    "slaves": [
                        "dummy8",
                        "dummy9"
                    ]
                }

            }
        }
        logger.info("Perform SetupNetwork action on %s",  c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % c.HOST_0
            )

    @polarion("RHEVM3-9851")
    def test_02_multiple_actions(self):
        """
        Move network from NIC to existing BOND
        Change NIC for existing network
        Add slave to existing BOND and Move network from another BOND to it
        Create new BOND with network attached to it
        Remove network from NIC
        Remove network from BOND
        Remove BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": "bond241",
                    "network": c.SN_NETS[24][1],
                },
                "2": {
                    "nic": "dummy3",
                    "network": c.SN_NETS[24][2],
                    "ip": c.BASIC_IP_DICT_PREFIX
                },
                "3": {
                    "nic": "bond242",
                    "network": c.SN_NETS[24][4],
                },
                "4": {
                    "nic": "bond242",
                    "slaves": [
                        "dummy1",
                        "dummy2",
                        "dummy4"
                    ]
                },
                "5": {
                    "nic": "bond243",
                    "slaves": [
                        "dummy5",
                        "dummy6",
                    ]
                },
            },
            "remove": {
                "networks": [c.SN_NETS[24][0], c.SN_NETS[24][3]],
                "bonds": ["bond244"]
            },
            "add": {
                "1": {
                    "nic": "bond243",
                    "network": c.SN_NETS[24][5]
                }
            }
        }
        logger.info("Perform SetupNetwork update action on %s",  c.HOST_0)
        if not hl_host_network.setup_networks(
            c.HOSTS[0], **network_host_api_dict
        ):
            raise c.NET_EXCEPTION(
                "Update SetupNetwork action failed on %s" % c.HOST_0
            )
