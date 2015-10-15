#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
"""

import helper
import logging
import config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_SN_Cases")


def setup_module():
    """
    Add networks
    """
    logger.info(
        "Add %s to %s/%s", conf.SN_DICT, conf.DC_NAME, conf.CLUSTER_2
    )
    helper.prepare_networks_on_dc(networks_dict=conf.SN_DICT)


def teardown_module():
    """
    Removes networks
    """
    helper.remove_networks_from_setup()


class TestHostNetworkApiSetupNetworks01(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10470")
    def test_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[1][0],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[1][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[1][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks02(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10472")
    def test_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[2][0],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[2][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[2][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks03(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10471")
    def test_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[3][0],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[3][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[3][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks04(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10474")
    def test_ip_network_on_host(self):
        """
        Attach network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[4][0],
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": conf.SN_NETS[4][1],
                    "nic": conf.HOST_4_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            conf.SN_NETS[4][0], conf.SN_NETS[4][1], conf.HOST_4_NICS[1],
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    conf.SN_NETS[4][0], conf.SN_NETS[4][1],
                    conf.HOST_4_NICS[1], conf.HOST_4_NICS[2], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks05(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10475")
    def test_ip_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[5][0],
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": conf.SN_NETS[5][1],
                    "nic": conf.HOST_4_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            conf.SN_NETS[5][0], conf.SN_NETS[5][1], conf.HOST_4_NICS[1],
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    conf.SN_NETS[5][0], conf.SN_NETS[5][1],
                    conf.HOST_4_NICS[1], conf.HOST_4_NICS[2], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks06(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10476")
    def test_ip_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask and prefix) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[6][0],
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": conf.SN_NETS[6][1],
                    "nic": conf.HOST_4_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            conf.SN_NETS[6][0], conf.SN_NETS[6][1], conf.HOST_4_NICS[1],
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    conf.SN_NETS[6][0], conf.SN_NETS[6][1],
                    conf.HOST_4_NICS[1], conf.HOST_4_NICS[2], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks07(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10478")
    def test_network_custom_properties_on_host(self):
        """
        Attach network with custom properties to host NIC
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_4_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[7][0],
                    "nic": conf.HOST_4_NICS[1],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[7][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[7][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks08(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True

    @polarion("RHEVM3-10513")
    def test_network_mtu_on_host(self):
        """
        Attach Non-VM network with 5000 MTU size to host NIC and try to attach
        VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[8][0],
                    "nic": conf.HOST_4_NICS[1]
                },
                "2": {
                    "network": conf.SN_NETS[8][1],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s(MTU5000) and %s(MTU9000) to %s on %s",
            conf.SN_NETS[8][0], conf.SN_NETS[8][0], conf.HOST_4_NICS[1],
            conf.HOST_4
        )
        if hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "%s and %s is attached to %s on %s but shouldn't" % (
                    conf.SN_NETS[8][0], conf.SN_NETS[8][1],
                    conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks09(helper.TestHostNetworkApiTestCaseBase):
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
                    "network": conf.SN_NETS[9][0],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[9][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[9][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )

    @polarion("RHEVM3-10514")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        network_host_api_dict = {
            "remove": {
                "networks": [conf.SN_NETS[9][0]]
                }
            }
        logger.info(
            "Removing %s from %s on %s",
            conf.SN_NETS[9][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s from %s on %s" % (
                    conf.SN_NETS[9][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks10(helper.TestHostNetworkApiTestCaseBase):
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
                    "network": conf.SN_NETS[10][0],
                    "nic": conf.HOST_4_NICS[1]
                },
                "2": {
                    "network": conf.SN_NETS[10][1],
                    "nic": conf.HOST_4_NICS[2]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[10][0], conf.HOST_4_NICS[1], conf.HOST_4)
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[10][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )

    @polarion("RHEVM3-10515")
    def test_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP (netmask and prefix)
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": conf.SN_NETS[10][0],
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": conf.SN_NETS[10][1],
                    "nic": conf.HOST_4_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Updating %s and %s to have IP on %s and %s of %s",
            conf.SN_NETS[10][0], conf.SN_NETS[10][1], conf.HOST_4_NICS[1],
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update %s and %s to have IP on %s and %s of %s" % (
                    conf.SN_NETS[10][0], conf.SN_NETS[10][0],
                    conf.HOST_4_NICS[1], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks11(helper.TestHostNetworkApiTestCaseBase):
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
        logger.info("Creating bond11 on %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond11 on %s" % conf.HOST_4
            )

    @polarion("RHEVM3-10516")
    def test_attach_networks_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[11][0],
                    "nic": "bond11"
                },
                "2": {
                    "nic": "bond11",
                    "network": conf.SN_NETS[11][1]
                },
                "3": {
                    "nic": "bond11",
                    "network": conf.SN_NETS[11][2]
                }
            }
        }
        logger.info(
            "Attach %s to bond11 on %s", conf.SN_NETS[11][0], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to bond11 on %s" % (
                    conf.SN_NETS[11][0], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks12(helper.TestHostNetworkApiTestCaseBase):
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
                    "slaves": conf.DUMMYS[:2],
                    "mode": 1
                }
            }
        }
        logger.info("Creating bond12 on %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond12 on %s" % conf.HOST_4
            )

    @polarion("RHEVM3-9622")
    def test_02update_bond_add_slave(self):
        """
        Add slave to BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": "bond12",
                    "slaves": conf.DUMMYS[:3]
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update bond12 to have 3 slaves on %s" %
                conf.HOST_4
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
                    "slaves": conf.DUMMYS[:2]
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update bond12 to have 2 slaves on %s" %
                conf.HOST_4
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
                    "slaves": conf.DUMMYS[:2],
                    "mode": "1"
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to update bond12 mode to mode 1 on %s" % conf.HOST_4
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
                    "network": conf.SN_NETS[12][0],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s with IP to bond12 on %s" %
                (conf.SN_NETS[14][0], conf.HOST_4)
            )


class TestHostNetworkApiSetupNetworks13(helper.TestHostNetworkApiTestCaseBase):
    """
    Create 3 BONDs
    """
    __test__ = True

    @polarion("RHEVM3-10518")
    def test_create_bonds(self):
        """
        Create BONDs
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond131",
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": "bond132",
                    "slaves": conf.DUMMYS[2:4]
                },
                "3": {
                    "nic": "bond133",
                    "slaves": conf.DUMMYS[4:6]
                }
            }
        }
        logger.info("Creating bond131/2/3 on %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond131/2/3 on %s" % conf.HOST_4
            )


class TestHostNetworkApiSetupNetworks14(helper.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with 5 slaves
    """
    __test__ = True

    @polarion("RHEVM3-10519")
    def test_create_bond_with_5_slaves(self):
        """
        Create BOND with 5 slaves
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond14",
                    "slaves": conf.DUMMYS[:5]
                }
            }
        }
        logger.info("Creating bond14 on %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond14 on %s" % conf.HOST_4
            )


class TestHostNetworkApiSetupNetworks15(helper.TestHostNetworkApiTestCaseBase):
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
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": conf.SN_NETS[15][0],
                    "nic": "bond15"
                },
                "3": {
                    "nic": "bond15",
                    "network": conf.SN_NETS[15][1]
                },
                "4": {
                    "nic": "bond15",
                    "network": conf.SN_NETS[15][2]
                }
            }
        }
        logger.info("Creating bond15 on %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond15 on %s" % conf.HOST_4
            )

    @polarion("RHEVM3-10517")
    def test_remove_networks_from_bond_host(self):
        """
        Remove network from BOND
        """
        network_host_api_dict = {
            "remove": {
                "networks": [conf.SN_NETS[15][1], conf.SN_NETS[15][2]]
            }
        }
        logger.info(
            "Removing %s and %s from bond15 on %s",
            conf.SN_NETS[15][1], conf.SN_NETS[15][2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s and %s from bond15 on %s" % (
                    conf.SN_NETS[15][1], conf.SN_NETS[15][2], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks16(helper.TestHostNetworkApiTestCaseBase):
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
            cls.unmamanged_net, conf.DC_NAME, conf.CLUSTER_2
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME, cluster=conf.CLUSTER_2,
            network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add network to %s/%s" %
                (conf.DC_NAME, conf.CLUSTER_2)
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
            "Create bond16 with %s on %s", conf.HOST_4, cls.unmamanged_net
        )
        if not hl_host_network.setup_networks(conf.HOST_4, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to create bond16 with %s on %s" %
                (cls.unmamanged_net, conf.HOST_4)
            )
        if not hl_networks.removeNetwork(
            True, cls.unmamanged_net, conf.DC_NAME
        ):
            raise conf.NET_EXCEPTION(
                "Failed to delete %s from %s" %
                (cls.unmamanged_net, conf.DC_NAME)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            conf.HOST_4, [cls.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    @polarion("RHEVM3-11432")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        logger.info("Removing %s from %s", self.unmamanged_net, conf.HOST_4)
        if not hl_host_network.clean_host_interfaces(conf.HOST_4):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s from %s" %
                (self.unmamanged_net, conf.HOST_4)
            )


class TestHostNetworkApiSetupNetworks17(helper.TestHostNetworkApiTestCaseBase):
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
            cls.unmamanged_net, conf.DC_NAME, conf.CLUSTER_2
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME, cluster=conf.CLUSTER_2,
            network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add network to %s/%s" %
                (conf.DC_NAME, conf.CLUSTER_2)
            )
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": cls.unmamanged_net
                }
            }
        }
        logger.info(
            "Create bond16 with %s on %s", conf.HOST_4, cls.unmamanged_net
        )
        if not hl_host_network.setup_networks(conf.HOST_4, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s on %s" % (cls.unmamanged_net, conf.HOST_4)
            )
        if not hl_networks.removeNetwork(
            True, cls.unmamanged_net, conf.DC_NAME
        ):
            raise conf.NET_EXCEPTION(
                "Failed to delete %s from %s" %
                (cls.unmamanged_net, conf.DC_NAME)
            )
        logger.info("Checking if %s is unmanaged network", cls.unmamanged_net)
        if not ll_host_network.get_host_unmanaged_networks(
            conf.HOST_4, [cls.unmamanged_net]
        ):
            raise conf.NET_EXCEPTION(
                "%s should be unmanaged network but it is not" %
                cls.unmamanged_net
            )

    @polarion("RHEVM3-12164")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        logger.info("Removing %s from %s", self.unmamanged_net, conf.HOST_4)
        if not hl_host_network.clean_host_interfaces(conf.HOST_4):
            raise conf.NET_EXCEPTION(
                "Failed to remove %s from %s" %
                (self.unmamanged_net, conf.HOST_4)
            )


class TestHostNetworkApiSetupNetworks18(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True

    @polarion("RHEVM3-11880")
    def test_network_custom_properties_on_bond_host(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_4_NICS[1], state="off"
            )
        }
        sn_dict = {
            "add": {
                "1": {
                    "nic": "bond18",
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": "bond18",
                    "network": conf.SN_NETS[18][0],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to bond18 on %s",
            conf.SN_NETS[18][0], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **sn_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to bond18 on %s" % (
                    conf.SN_NETS[18][0], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks19(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10477")
    def test_ip_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[19][0],
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": conf.SN_NETS[19][1],
                    "nic": conf.HOST_4_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        logger.info(
            "Attaching %s and %s to %s and %s on %s",
            conf.SN_NETS[19][0], conf.SN_NETS[19][1], conf.HOST_4_NICS[1],
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s and %s on %s" % (
                    conf.SN_NETS[19][0], conf.SN_NETS[19][1],
                    conf.HOST_4_NICS[1], conf.HOST_4_NICS[2], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks20(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-10473")
    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": conf.SN_NETS[20][0],
                    "nic": conf.HOST_4_NICS[1]
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            conf.SN_NETS[20][0], conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    conf.SN_NETS[20][0], conf.HOST_4_NICS[1], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks21(helper.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with network
    """
    __test__ = True

    @polarion("RHEVM3-10438")
    def test_attach_networks_to_bond(self):
        """
        Create BOND with network
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond21",
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": conf.SN_NETS[21][0],
                    "nic": "bond21"
                }
            }
        }
        logger.info(
            "Attach %s to bond21 on %s", conf.SN_NETS[21][0], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to bond21 on %s" % (
                    conf.SN_NETS[21][0], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks22(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to host NIC
    """
    __test__ = True

    @polarion("RHEVM3-9823")
    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[22][0]
                },
                "2": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[22][1]
                },
                "3": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[22][2]
                }
            }
        }
        logger.info(
            "Attaching %s,%s and %s to %s on %s", conf.SN_NETS[22][0],
            conf.SN_NETS[22][1], conf.SN_NETS[22][2], conf.HOST_4_NICS[1],
            conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s, %s and %s to %s on %s" %
                (conf.SN_NETS[22][0], conf.SN_NETS[22][1], conf.SN_NETS[22][2],
                 conf.HOST_4_NICS[1], conf.HOST_4)
            )


class TestHostNetworkApiSetupNetworks23(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to BOND
    """
    __test__ = True

    @polarion("RHEVM3-9824")
    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": "bond23",
                    "network": conf.SN_NETS[23][0]
                },
                "2": {
                    "nic": "bond23",
                    "network": conf.SN_NETS[23][1]
                },
                "3": {
                    "nic": "bond23",
                    "network": conf.SN_NETS[23][2]
                },
                "4": {
                    "nic": "bond23",
                    "slaves": conf.DUMMYS[:2]
                }
            }
        }
        logger.info(
            "Attaching %s,%s and %s to bond23 on %s", conf.SN_NETS[23][0],
            conf.SN_NETS[23][1], conf.SN_NETS[23][2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s, %s and %s to bond23 on %s" %
                (conf.SN_NETS[23][0], conf.SN_NETS[23][1], conf.SN_NETS[23][2],
                 conf.HOST_4)
            )


class TestHostNetworkApiSetupNetworks24(helper.TestHostNetworkApiTestCaseBase):
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
    bz = {"1269481": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @polarion("RHEVM3-9850")
    def test_01_multiple_actions(self):
        """
        Attach Non-VM + 2 VLAN networks (IP and custom properties) to NIC1
        Create BOND and attach Non-VM + 1 VLAN network with IP to BOND
        Create empty BOND
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_4_NICS[2], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[24][0]
                },
                "2": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[24][1],
                },
                "3": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": conf.SN_NETS[24][2],
                    "ip": conf.BASIC_IP_DICT_PREFIX,
                    "properties": properties_dict
                },
                "4": {
                    "nic": "bond241",
                    "slaves": conf.DUMMYS[:2]
                },
                "5": {
                    "nic": "bond241",
                    "network": conf.SN_NETS[24][3],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "6": {
                    "nic": "bond241",
                    "network": conf.SN_NETS[24][4],
                },
                "7": {
                    "nic": "bond242",
                    "slaves": conf.DUMMYS[2:4]
                },
                "8": {
                    "nic": "bond243",
                    "slaves": conf.DUMMYS[6:9]
                },
                "9": {
                    "nic": "bond244",
                    "slaves": conf.DUMMYS[9:11]
                }

            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_4
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
                    "network": conf.SN_NETS[24][1],
                },
                "2": {
                    "nic": conf.DUMMYS[11],
                    "network": conf.SN_NETS[24][2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                },
                "3": {
                    "nic": "bond242",
                    "network": conf.SN_NETS[24][4],
                },
                "4": {
                    "nic": "bond242",
                    "slaves": conf.DUMMYS[2:5]
                },
                "5": {
                    "nic": "bond243",
                    "slaves": conf.DUMMYS[6:8]
                },
            },
            "remove": {
                "networks": [conf.SN_NETS[24][0], conf.SN_NETS[24][3]],
                "bonds": ["bond244"]
            },
            "add": {
                "1": {
                    "nic": "bond243",
                    "network": conf.SN_NETS[24][5]
                }
            }
        }
        logger.info("Perform SetupNetwork update action on %s",  conf.HOST_4)
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Update SetupNetwork action failed on %s" % conf.HOST_4
            )


class TestHostNetworkApiSetupNetworks25(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VM network to host NIC that has VLAN network on it
    Attach VLAN network to host NIC that has VM network on it
    Attach VLAN network and VM network to same host NIC
    """
    __test__ = True
    net_case_pre_vm = conf.SN_NETS[25][0]
    net_case_pre_vlan = conf.SN_NETS[25][1]
    net_case_vlan = conf.SN_NETS[25][2]
    net_case_vm = conf.SN_NETS[25][3]
    net_case_new_vm = conf.SN_NETS[25][4]
    net_case_new_vlan = conf.SN_NETS[25][5]

    @classmethod
    def setup_class(cls):
        """
        Attach VM and VLAN network to host NICs
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": cls.net_case_pre_vm
                },
                "2": {
                    "nic": conf.HOST_4_NICS[2],
                    "network": cls.net_case_pre_vlan
                }
            }
        }
        if not hl_host_network.setup_networks(conf.HOST_4, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s on %s" %
                (cls.net_case_pre_vm, cls.net_case_pre_vlan, conf.HOST_4)
            )

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[1],
                    "network": self.net_case_vlan
                },
            }
        }
        logger.info(
            "Attaching %s to %s on %s", self.net_case_vlan,
            conf.HOST_4_NICS[1], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (self.net_case_vlan, conf.HOST_4_NICS[1], conf.HOST_4)
            )

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[2],
                    "network": self.net_case_vm
                },
            }
        }
        logger.info(
            "Attaching %s to %s on %s", self.net_case_vm,
            conf.HOST_4_NICS[2], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (self.net_case_vm, conf.HOST_4_NICS[2], conf.HOST_4)
            )

    def test_attach_vm_and_vlan_network_to_host_nic(self):
        """
        Attach VLAN network and VM network to same host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_4_NICS[3],
                    "network": self.net_case_new_vm
                },
                "2": {
                    "nic": conf.HOST_4_NICS[3],
                    "network": self.net_case_new_vlan
                },
            }
        }
        logger.info(
            "Attaching %s and %s to %s on %s", self.net_case_new_vm,
            self.net_case_new_vlan, conf.HOST_4_NICS[3], conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s on %s" %
                (
                    self.net_case_new_vm, self.net_case_new_vlan,
                    conf.HOST_4_NICS[3], conf.HOST_4
                )
            )


class TestHostNetworkApiSetupNetworks26(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VM network to BOND that has VLAN network on it
    Attach VLAN network to BOND that has VM network on it
    Attach VLAN network and VM network to same BOND
    """
    __test__ = True
    net_case_pre_vm = conf.SN_NETS[26][0]
    net_case_pre_vlan = conf.SN_NETS[26][1]
    net_case_vlan = conf.SN_NETS[26][2]
    net_case_vm = conf.SN_NETS[26][3]
    net_case_new_vm = conf.SN_NETS[26][4]
    net_case_new_vlan = conf.SN_NETS[26][5]
    bond_1 = "bond261"
    bond_2 = "bond262"
    bond_3 = "bond263"

    @classmethod
    def setup_class(cls):
        """
        Create 3 BONDs
        Attach VM network to first BOND
        Attach VLAN network to second BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": cls.bond_2,
                    "slaves": conf.DUMMYS[2:4]
                },
                "3": {
                    "nic": cls.bond_3,
                    "slaves": conf.DUMMYS[4:6]
                },
                "4": {
                    "nic": cls.bond_1,
                    "network": cls.net_case_pre_vm
                },
                "5": {
                    "nic": cls.bond_2,
                    "network": cls.net_case_pre_vlan
                }
            }
        }
        if not hl_host_network.setup_networks(conf.HOST_4, **sn_dict):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s on %s" %
                (cls.net_case_pre_vm, cls.net_case_pre_vlan, conf.HOST_4)
            )

    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "network": self.net_case_vlan
                },
            }
        }
        logger.info(
            "Attaching %s to %s on %s", self.net_case_vlan,
            self.bond_1, conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (self.net_case_vlan, self.bond_1, conf.HOST_4)
            )

    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "network": self.net_case_vm
                },
            }
        }
        logger.info(
            "Attaching %s to %s on %s", self.net_case_vm,
            self.bond_2, conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (self.net_case_vm, self.bond_2, conf.HOST_4)
            )

    def test_attach_vm_and_vlan_network_to_host_nic(self):
        """
        Attach VLAN network and VM network to same host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_3,
                    "network": self.net_case_new_vm
                },
                "2": {
                    "nic": self.bond_3,
                    "network": self.net_case_new_vlan
                },
            }
        }
        logger.info(
            "Attaching %s and %s to %s on %s", self.net_case_new_vm,
            self.net_case_new_vlan, self.bond_3, conf.HOST_4
        )
        if not hl_host_network.setup_networks(
            conf.HOST_4, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s on %s" %
                (
                    self.net_case_new_vm, self.net_case_new_vlan,
                    self.bond_3, conf.HOST_4
                )
            )
