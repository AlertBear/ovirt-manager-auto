#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
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

logger = logging.getLogger("Host_Network_API_SN_Cases")


def setup_module():
    """
    Add networks
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.SN_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks
    """
    network_helper.remove_networks_from_setup()


class TestHostNetworkApiSetupNetworks01(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network to host NIC
    """
    __test__ = True
    net = conf.SN_NETS[1][0]

    @polarion("RHEVM3-10470")
    def test_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks02(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network to host NIC
    """
    __test__ = True
    net = conf.SN_NETS[2][0]

    @polarion("RHEVM3-10472")
    def test_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks03(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True
    net = conf.SN_NETS[3][0]

    @polarion("RHEVM3-10471")
    def test_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks04(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with IP (netmask) to host NIC
    Attach network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[23]
    ip_prefix = conf.IPS[24]
    net_1 = conf.SN_NETS[4][0]
    net_2 = conf.SN_NETS[4][1]

    @polarion("RHEVM3-10474")
    def test_ip_network_on_host(self):
        """
        Attach network with IP (netmask and prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks05(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach VLAN network with IP (netmask) to host NIC
    Attach VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[29]
    ip_prefix = conf.IPS[30]
    net_1 = conf.SN_NETS[5][0]
    net_2 = conf.SN_NETS[5][1]

    @polarion("RHEVM3-10475")
    def test_ip_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask and prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks06(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM network with IP (netmask) to host NIC
    Attach Non-VM network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[25]
    ip_prefix = conf.IPS[26]
    net_1 = conf.SN_NETS[6][0]
    net_2 = conf.SN_NETS[6][1]

    @polarion("RHEVM3-10476")
    def test_ip_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask and prefix) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks07(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach label to host NIC
    """
    __test__ = True
    label = conf.LABEL_LIST[0]

    @polarion("RHEVM3-12411")
    def test_label_on_host_nic(self):
        """
        Attach label to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "labels": [self.label],
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks08(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach Non-VM network with 5000 MTU size to host NIC
    2.Try to attach VLAN network with 9000 MTU size to the same NIC
    """
    __test__ = True
    net_1 = conf.SN_NETS[8][0]
    net_2 = conf.SN_NETS[8][1]

    @polarion("RHEVM3-10513")
    def test_network_mtu_on_host(self):
        """
        Attach Non-VM network with 5000 MTU size to host NIC and try to attach
        VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks09(helper.TestHostNetworkApiTestCaseBase):
    """
    Remove network from host NIC
    """
    __test__ = True
    net = conf.SN_NETS[9][0]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10514")
    def test_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        network_host_api_dict = {
            "remove": {
                "networks": [self.net]
                }
            }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks10(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Attach networks to host NICs
    2.Update the network to have IP (netmask)
    3.Update the network to have IP (prefix)
    """
    __test__ = True
    ip_netmask = conf.IPS[31]
    ip_prefix = conf.IPS[32]
    net_1 = conf.SN_NETS[10][0]
    net_2 = conf.SN_NETS[10][1]

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

    @polarion("RHEVM3-10515")
    def test_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP (netmask and prefix)
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks11(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND
    2.Attach network to BOND
    """
    __test__ = True
    bond = "bond11"
    dummys = conf.DUMMYS[:2]
    net_1 = conf.SN_NETS[11][0]
    net_2 = conf.SN_NETS[11][1]
    net_3 = conf.SN_NETS[11][2]

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

    @polarion("RHEVM3-10516")
    def test_attach_networks_to_bond(self):
        """
        Attach network to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": self.bond
                },
                "2": {
                    "nic": self.bond,
                    "network": self.net_2
                },
                "3": {
                    "nic": self.bond,
                    "network": self.net_3
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks12(helper.TestHostNetworkApiTestCaseBase):
    """
    1. Create BOND
    2. Add slave to BOND
    3. Remove slaves from BOND
    4. Update BOND mode
    5. Attach network with IP to BOND
    """
    __test__ = True
    ip_netmask = conf.IPS[22]
    bond = "bond12"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[:3]
    net = conf.SN_NETS[12][0]

    @polarion("RHEVM3-9621")
    def test_01create_bond(self):
        """
        Create BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys_1,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-9622")
    def test_02update_bond_add_slave(self):
        """
        Add slave to BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys_2
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10520")
    def test_03update_bond_remove_slave(self):
        """
        Remove slave from BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys_1
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-9642")
    def test_04update_bond_mode(self):
        """
        Update BOND to mode 1
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys_1,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10521")
    def test_05update_bond_with_ip(self):
        """
        Attach network with IP to BOND
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "network": self.net,
                    "ip": conf.BASIC_IP_DICT_NETMASK
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks13(helper.TestHostNetworkApiTestCaseBase):
    """
    Create 3 BONDs
    """
    __test__ = True
    bond_1 = "bond131"
    bond_2 = "bond132"
    bond_3 = "bond133"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]
    dummys_3 = conf.DUMMYS[4:6]

    @polarion("RHEVM3-10518")
    def test_create_bonds(self):
        """
        Create BONDs
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": self.dummys_1
                },
                "2": {
                    "nic": self.bond_2,
                    "slaves": self.dummys_2
                },
                "3": {
                    "nic": self.bond_3,
                    "slaves": self.dummys_3
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks14(helper.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with 5 slaves
    """
    __test__ = True
    bond = "bond14"
    dummys = conf.DUMMYS[:5]

    @polarion("RHEVM3-10519")
    def test_create_bond_with_5_slaves(self):
        """
        Create BOND with 5 slaves
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks15(helper.TestHostNetworkApiTestCaseBase):
    """
    1.Create BOND with 3 networks
    2.Remove networks from BOND
    """
    __test__ = True
    bond = "bond15"
    dummys = conf.DUMMYS[:2]
    net_1 = conf.SN_NETS[15][0]
    net_2 = conf.SN_NETS[15][1]
    net_3 = conf.SN_NETS[15][2]

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
                },
                "2": {
                    "network": cls.net_1,
                    "nic": cls.bond
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

    @polarion("RHEVM3-10517")
    def test_remove_networks_from_bond_host(self):
        """
        Remove network from BOND
        """
        network_host_api_dict = {
            "remove": {
                "networks": [self.net_2, self.net_3]
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks16(helper.TestHostNetworkApiTestCaseBase):
    """
    1. Create network on DC/Cluster/Host (BOND)
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    unmamanged_net = "unman_sn_16"
    dummys = conf.DUMMYS[:2]
    bond = "bond16"

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

    @polarion("RHEVM3-11432")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_0_NAME):
            raise conf.NET_EXCEPTION()


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
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0, network_dict=network_dict
        ):
            raise conf.NET_EXCEPTION()

        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
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

    @polarion("RHEVM3-12164")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_0_NAME):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks18(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach network with custom properties to BOND
    """
    __test__ = True
    bond = "bond18"
    dummys = conf.DUMMYS[:2]
    net = conf.SN_NETS[18][0]

    @polarion("RHEVM3-11880")
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
        sn_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys
                },
                "2": {
                    "nic": self.bond,
                    "network": self.net,
                    "properties": properties_dict
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks19(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network with IP (netmask) to host NIC
    Attach Non-VM VLAN network with IP (prefix) to host NIC
    """
    __test__ = True
    ip_netmask = conf.IPS[27]
    ip_prefix = conf.IPS[28]
    net_1 = conf.SN_NETS[19][0]
    net_2 = conf.SN_NETS[19][1]

    @polarion("RHEVM3-10477")
    def test_ip_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = self.ip_prefix
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = self.ip_netmask
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks20(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach Non-VM VLAN network to host NIC
    """
    __test__ = True
    net = conf.SN_NETS[20][0]

    @polarion("RHEVM3-10473")
    def test_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks21(helper.TestHostNetworkApiTestCaseBase):
    """
    Create BOND with network
    """
    __test__ = True
    bond = "bond21"
    dummys = conf.DUMMYS[:2]
    net = conf.SN_NETS[21][0]

    @polarion("RHEVM3-10438")
    def test_attach_networks_to_bond(self):
        """
        Create BOND with network
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": self.dummys
                },
                "2": {
                    "network": self.net,
                    "nic": self.bond
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks22(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to host NIC
    """
    __test__ = True
    net_1 = conf.SN_NETS[22][0]
    net_2 = conf.SN_NETS[22][1]
    net_3 = conf.SN_NETS[22][2]

    @polarion("RHEVM3-9823")
    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net_1
                },
                "2": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net_2
                },
                "3": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net_3
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks23(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach multiple VLANs to BOND
    """
    __test__ = True
    bond = "bond23"
    dummys = conf.DUMMYS[:2]
    net_1 = conf.SN_NETS[23][0]
    net_2 = conf.SN_NETS[23][1]
    net_3 = conf.SN_NETS[23][2]

    @polarion("RHEVM3-9824")
    def test_remove_networks_from_bond_host(self):
        """
        Attach multiple VLANs to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "network": self.net_1
                },
                "2": {
                    "nic": self.bond,
                    "network": self.net_2
                },
                "3": {
                    "nic": self.bond,
                    "network": self.net_3
                },
                "4": {
                    "nic": self.bond,
                    "slaves": self.dummys
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


class TestHostNetworkApiSetupNetworks24(helper.TestHostNetworkApiTestCaseBase):
    """
    Attach label to BOND
    """
    __test__ = True
    bond_1 = "bond281"
    dummys = conf.DUMMYS[:2]
    label = conf.LABEL_LIST[0]

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": cls.dummys
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-12412")
    def test_label_on_bond(self):
        """
        Attach label to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "labels": [self.label],
                    "nic": self.bond_1
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


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

    @polarion("RHEVM3-14016")
    def test_attach_vlan_to_host_nic_with_vm(self):
        """
        Attach VLAN network to host NIC that has VM network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net_case_vlan
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14015")
    def test_attach_vm_to_host_nic_with_vlan(self):
        """
        Attach VM network to host NIC that has VLAN network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[2],
                    "network": self.net_case_vm
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14017")
    def test_attach_vm_and_vlan_network_to_host_nic(self):
        """
        Attach VLAN network and VM network to same host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[3],
                    "network": self.net_case_new_vm
                },
                "2": {
                    "nic": conf.HOST_0_NICS[3],
                    "network": self.net_case_new_vlan
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()


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
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]
    dummys_3 = conf.DUMMYS[4:6]

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
                    "slaves": cls.dummys_1
                },
                "2": {
                    "nic": cls.bond_2,
                    "slaves": cls.dummys_2
                },
                "3": {
                    "nic": cls.bond_3,
                    "slaves": cls.dummys_3
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
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14019")
    def test_attach_vlan_to_bond_with_vm_net(self):
        """
        Attach VLAN network to BOND that has VM network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "network": self.net_case_vlan
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14018")
    def test_attach_vm_net_to_bond_with_vlan(self):
        """
        Attach VM network to BOND that has VLAN network on it
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "network": self.net_case_vm
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14020")
    def test_attach_vm_and_vlan_networks_to_bond(self):
        """
        Attach VLAN network and VM network to same BOND
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
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()
