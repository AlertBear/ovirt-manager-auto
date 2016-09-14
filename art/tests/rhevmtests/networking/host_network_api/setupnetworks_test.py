#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.network_custom_properties.config as cust_prop_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import create_network_in_dc_and_cluster, remove_network
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)


@pytest.fixture(scope="module", autouse=True)
def sn_prepare_setup(request):
    """
    Prepare setup for setup networks tests
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=net_api_conf.SN_DICT, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(clean_host_interfaces.__name__)
class TestHostNetworkApiSetupNetworks01(NetworkTest):
    """
    1) Attach network to host NIC.
    2) Attach VLAN network to host NIC.
    3) Update the network to have IP (netmask).
    4) Update the network to have IP (prefix).
    5) Remove network from host NIC.
    6) Attach Non-VM network to host NIC.
    7) Attach network with IP (netmask) to host NIC.
    8) Attach network with IP (prefix) to host NIC.
    9) Attach VLAN network with IP (netmask) to host NIC.
    10) Attach VLAN network with IP (prefix) to host NIC.
    11) Attach Non-VM network with IP (netmask) to host NIC.
    12) Attach Non-VM network with IP (prefix) to host NIC.
    13) Attach label to host NIC.
    14) Attach Non-VM network with 5000 MTU size to host NIC.
    15) Try to attach VLAN network with 9000 MTU size to the same NIC.
    16) Attach Non-VM VLAN network with IP (netmask) to host NIC.
    17) Attach Non-VM VLAN network with IP (prefix) to host NIC.
    18) Attach Non-VM VLAN network to host NIC.
    19) Attach multiple VLANs to host NIC.
    """
    __test__ = True
    net_1 = net_api_conf.SN_NETS[1][0]
    ip_netmask_net_1 = net_api_conf.IPS[31]
    net_2 = net_api_conf.SN_NETS[1][1]
    ip_prefix_net_2 = net_api_conf.IPS[32]
    net_3 = net_api_conf.SN_NETS[1][2]
    net_4 = net_api_conf.SN_NETS[1][3]
    ip_netmask_net_4 = net_api_conf.IPS[23]
    net_5 = net_api_conf.SN_NETS[1][4]
    ip_prefix_net_5 = net_api_conf.IPS[24]
    net_6 = net_api_conf.SN_NETS[1][5]
    ip_netmask_net_6 = net_api_conf.IPS[29]
    net_7 = net_api_conf.SN_NETS[1][6]
    ip_prefix_net_7 = net_api_conf.IPS[30]
    net_8 = net_api_conf.SN_NETS[1][7]
    ip_netmask_net_8 = net_api_conf.IPS[25]
    net_9 = net_api_conf.SN_NETS[1][8]
    ip_prefix_net_9 = net_api_conf.IPS[26]
    net_10 = net_api_conf.SN_NETS[1][9]
    net_11 = net_api_conf.SN_NETS[1][10]
    net_12 = net_api_conf.SN_NETS[1][11]
    ip_netmask_net_12 = net_api_conf.IPS[27]
    net_13 = net_api_conf.SN_NETS[1][12]
    ip_prefix_net_13 = net_api_conf.IPS[28]
    net_14 = net_api_conf.SN_NETS[1][13]
    net_15 = net_api_conf.SN_NETS[1][14]
    net_16 = net_api_conf.SN_NETS[1][15]
    net_17 = net_api_conf.SN_NETS[1][16]
    label = conf.LABEL_LIST[0]
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-10470")
    def test_01_network_on_host_nic(self):
        """
        Attach network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        testflow.step(
            "Attach network %s to host NIC %s", self.net_1, conf.HOST_0_NICS[1]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10472")
    def test_02_vlan_network_on_host_nic(self):
        """
        Attach VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2]
                }
            }
        }
        testflow.step(
            "Attach VLAN %s network to host NIC %s", self.net_2,
            conf.HOST_0_NICS[2]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10515")
    def test_03_update_network_with_ip_host_nic(self):
        """
        Update the network to have IP (netmask and prefix)
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_1
        )
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_2
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2],
                    "ip": net_api_conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        testflow.step(
            "Update the networks to have IP (netmask and prefix) %s",
            network_host_api_dict
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10514")
    def test_04_network_remove_from_host(self):
        """
        Remove network from host NIC
        """
        network_host_api_dict = {
            "remove": {
                "networks": [self.net_1]
            }
        }
        testflow.step(
            "Remove network %s from host NIC %s", self.net_1,
            conf.HOST_0_NICS[1]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10471")
    def test_05_non_vm_network_on_host_nic(self):
        """
        Attach Non-VM network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_3,
                    "nic": conf.HOST_0_NICS[3]
                }
            }
        }
        testflow.step(
            "Attach Non-VM network %s to host NIC %s", self.net_3,
            conf.HOST_0_NICS[3]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10474")
    def test_06_ip_network_on_host(self):
        """
        Attach network with IP (netmask and prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_4
        )
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_5
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": conf.HOST_0_NICS[4],
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_5,
                    "nic": conf.HOST_0_NICS[5],
                    "ip": net_api_conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        testflow.step(
            "Attach network with IP (netmask %s and prefix %s) to "
            "host NIC %s and %s", self.ip_netmask_net_4, self.ip_prefix_net_5,
            conf.HOST_0_NICS[4], conf.HOST_0_NICS[5]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10475")
    def test_07_ip_vlan_network_on_host(self):
        """
        Attach VLAN network with IP (netmask and prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_7
        )
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_6
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_6,
                    "nic": conf.HOST_0_NICS[6],
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_7,
                    "nic": conf.HOST_0_NICS[7],
                    "ip": net_api_conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        testflow.step(
            "Attach VLAN network with IP (netmask %s and prefix %s) "
            "to host NIC %s and %s ", self.ip_netmask_net_6,
            self.ip_prefix_net_7,  conf.HOST_0_NICS[6], conf.HOST_0_NICS[7]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10476")
    def test_08_ip_non_vm_network_on_host(self):
        """
        Attach Non-VM network with IP (netmask and prefix) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_8
        )
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_9
        )

        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_8,
                    "nic": conf.HOST_0_NICS[8],
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_9,
                    "nic": conf.HOST_0_NICS[9],
                    "ip": net_api_conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        testflow.step(
            "Attach Non-VM network with IP (netmask %s and prefix %s) "
            "to host NIC %s and %s", self.ip_netmask_net_8,
            self.ip_prefix_net_9, conf.HOST_0_NICS[8], conf.HOST_0_NICS[9],
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-12411")
    def test_09_label_on_host_nic(self):
        """
        Attach label to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "labels": [self.label],
                    "nic": conf.HOST_0_NICS[10]
                }
            }
        }
        testflow.step(
            "Attach label %s to host NIC %s", self.label, conf.HOST_0_NICS[10]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10513")
    def test_10_network_mtu_on_host(self):
        """
        Attach Non-VM network with 5000 MTU size to host NIC and try to attach
        VLAN network with 9000 MTU size to the same NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_10,
                    "nic": conf.HOST_0_NICS[11]
                },
                "2": {
                    "network": self.net_11,
                    "nic": conf.HOST_0_NICS[11]
                }
            }
        }
        testflow.step(
            "Attach Non-VM network %s with 5000 MTU size to host NIC %s and "
            "try to attach VLAN network %s with 9000 MTU size to "
            "the same NIC %s", self.net_10, conf.HOST_0_NICS[11], self.net_11,
            conf.HOST_0_NICS[11]
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10477")
    def test_11_ip_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network with IP (netmask) to host NIC
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_12
        )
        net_api_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = (
            self.ip_prefix_net_13
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_12,
                    "nic": conf.HOST_0_NICS[12],
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                },
                "2": {
                    "network": self.net_13,
                    "nic": conf.HOST_0_NICS[13],
                    "ip": net_api_conf.BASIC_IP_DICT_PREFIX
                }
            }
        }
        testflow.step(
            "Attach Non-VM VLAN networks %s and %s with IP (netmask) %s"
            "to host NIC %s and %s", self.net_12, self.net_13,
            network_host_api_dict, conf.HOST_0_NICS[12], conf.HOST_0_NICS[13]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10473")
    def test_12_non_vm_vlan_network_on_host(self):
        """
        Attach Non-VM VLAN network to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_14,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        testflow.step(
            "Attach Non-VM VLAN network %s to host NIC %s", self.net_14,
            conf.HOST_0_NICS[14]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-9823")
    def test_13_multiple_vlans_networks_on_host_nic(self):
        """
        Attach multiple VLANs to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[15],
                    "network": self.net_15
                },
                "2": {
                    "nic": conf.HOST_0_NICS[15],
                    "network": self.net_16
                },
                "3": {
                    "nic": conf.HOST_0_NICS[15],
                    "network": self.net_17
                }
            }
        }
        testflow.step(
            "Attach multiple VLANs %s %s %s to host NIC %s",
            self.net_15, self.net_16, self.net_17, conf.HOST_0_NICS[15]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(clean_host_interfaces.__name__)
class TestHostNetworkApiSetupNetworks02(NetworkTest):
    """
    1. Create BOND
    2. Add slave to BOND
    3. Remove slaves from BOND
    4. Update BOND mode
    5. Attach 3 networks to bond.
    6. Remove  3 networks from BOND.
    7. Attach network with IP to BOND
    8. Create 3 BONDs.
    9. Attach label to BOND.
    10. Create BOND with 5 slaves.
    11. Attach network with custom properties to BOND.
    """
    __test__ = True
    bond_5 = "bond025"
    bond_1 = "bond021"
    dummy_1 = [net_api_conf.DUMMYS[2]]
    net_1 = net_api_conf.SN_NETS[2][0]
    ip_netmask_net_1 = net_api_conf.IPS[22]
    dummys_1 = net_api_conf.DUMMYS[:2]
    bond_2 = "bond022"
    dummys_2 = net_api_conf.DUMMYS[2:4]
    bond_3 = "bond023"
    dummys_3 = net_api_conf.DUMMYS[4:6]
    bond_4 = "bond024"
    dummys_4 = net_api_conf.DUMMYS[6:8]
    dummys_5 = net_api_conf.DUMMYS[8:12]
    bond_6 = "bond026"
    dummys_6 = net_api_conf.DUMMYS[12:14]
    net_2 = net_api_conf.SN_NETS[2][1]
    net_4 = net_api_conf.SN_NETS[2][2]
    net_5 = net_api_conf.SN_NETS[2][3]
    net_6 = net_api_conf.SN_NETS[2][4]
    label_1 = conf.LABEL_LIST[0]
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    @polarion("RHEVM3-9621")
    def test_01_create_bond(self):
        """
        Create BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": self.dummys_1,
                }
            }
        }
        testflow.step("Create BOND %s", self.bond_1)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-9622")
    def test_02_update_bond_add_slave(self):
        """
        Add slave to BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": self.dummy_1
                }
            }
        }
        testflow.step("Add slave %s to BOND %s", self.dummy_1, self.bond_1)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10520")
    def test_03_update_bond_remove_slave(self):
        """
        Remove slave from BOND
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": self.dummy_1
                }
            }
        }
        testflow.step(
            "Remove slave %s from BOND %s", self.dummy_1, self.bond_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10516")
    def test_04_attach_networks_to_bond(self):
        """
        Attach networks to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_4,
                    "nic": self.bond_1
                },
                "2": {
                    "nic": self.bond_1,
                    "network": self.net_5
                },
                "3": {
                    "nic": self.bond_1,
                    "network": self.net_6
                }
            }
        }
        testflow.step(
            "Attach networks %s and %s and %s to BOND %s", self.net_4,
            self.net_5, self.net_6, self.bond_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10517")
    def test_05_remove_networks_from_bond_host(self):
        """
        Remove network from BOND
        """
        network_host_api_dict = {
            "remove": {
                "networks": [self.net_4, self.net_5, self.net_6]
            }
        }
        testflow.step(
            "Remove networks %s and %s and %s from BOND %s", self.net_4,
            self.net_5, self.net_6, self.bond_1

        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-9642")
    def test_06_update_bond_mode(self):
        """
        Update BOND to mode 1
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "nic": self.bond_1,
                    "mode": 1
                }
            }
        }
        testflow.step("Update BOND %s to mode 1", self.bond_1)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10521")
    def test_07_update_bond_with_ip(self):
        """
        Attach network with IP to BOND
        """
        net_api_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = (
            self.ip_netmask_net_1
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "network": self.net_1,
                    "ip": net_api_conf.BASIC_IP_DICT_NETMASK
                }
            }
        }
        testflow.step(
            "Attach network %s with IP %s to BOND %s", self.net_1,
            net_api_conf.BASIC_IP_DICT_NETMASK, self.bond_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10518")
    def test_08_create_bonds(self):
        """
        Create BONDs
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "slaves": self.dummys_2
                },
                "2": {
                    "nic": self.bond_3,
                    "slaves": self.dummys_3
                },
                "3": {
                    "nic": self.bond_4,
                    "slaves": self.dummys_4
                }
            }
        }
        testflow.step("Create 3 BONDs %s", network_host_api_dict)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-12412")
    def test_09_label_on_bond(self):
        """
        Attach label to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "labels": [self.label_1],
                    "nic": self.bond_4
                }
            }
        }
        testflow.step("Attach label %s to BOND %s", self.label_1, self.bond_4)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-10519")
    def test_10_create_bond_with_5_slaves(self):
        """
        Create BOND with 5 slaves
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_5,
                    "slaves": self.dummys_5
                }
            }
        }
        testflow.step(
            "Create BOND %s with 5 slaves %s", self.bond_5, self.dummys_5
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-11880")
    def test_11_network_custom_properties_on_bond_host(self):
        """
        Attach network with custom properties to BOND
        """
        properties_dict = {
            "bridge_opts": cust_prop_conf.PRIORITY,
            "ethtool_opts": cust_prop_conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_6,
                    "slaves": self.dummys_6
                },
                "2": {
                    "nic": self.bond_6,
                    "network": self.net_2,
                    "properties": properties_dict
                }
            }
        }
        testflow.step(
            "Attach network %s with custom properties %s to BOND %s",
            self.net_2, properties_dict, self.bond_6
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(clean_host_interfaces.__name__)
class TestHostNetworkApiSetupNetworks03(NetworkTest):
    """
    1. Create BOND with network.
    2. Attach multiple VLANs to BOND.
    """
    bond_1 = "bond031"
    dummys_1 = net_api_conf.DUMMYS[:2]
    net_1 = net_api_conf.SN_NETS[3][0]
    bond_2 = "bond32"
    dummys_2 = net_api_conf.DUMMYS[2:4]
    net_2 = net_api_conf.SN_NETS[3][1]
    net_3 = net_api_conf.SN_NETS[3][2]
    net_4 = net_api_conf.SN_NETS[3][3]

    @polarion("RHEVM3-10438")
    def test_01_attach_networks_to_bond(self):
        """
        Create BOND with network
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": self.dummys_1
                },
                "2": {
                    "network": self.net_1,
                    "nic": self.bond_1
                }
            }
        }
        testflow.step(
            "Create BOND %s with network %s", self.bond_1, self.net_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

    @polarion("RHEVM3-9824")
    def test_02_attach_multiple_vlans_networks_to_bond(self):
        """
        Attach multiple VLANs to BOND
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "network": self.net_2
                },
                "2": {
                    "nic": self.bond_2,
                    "network": self.net_3
                },
                "3": {
                    "nic": self.bond_2,
                    "network": self.net_4
                },
                "4": {
                    "nic": self.bond_2,
                    "slaves": self.dummys_2
                }
            }
        }
        testflow.step(
            "Attach multiple VLANs %s %s %s to BOND %s",
            self.net_2, self.net_3, self.net_4, self.bond_2
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_in_dc_and_cluster.__name__,
    setup_networks_fixture.__name__,
    remove_network.__name__
)
class TestHostNetworkApiSetupNetworks04(NetworkTest):
    """
    1. Create network on DC/Cluster/Host (BOND)
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    net = "unman_sn_04"
    bond = "bond04"
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [-1, -2]
            },
            net: {
                "nic": bond,
                "network": net
            }
        }
    }

    @polarion("RHEVM3-11432")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step(
            "Get unmanaged network %s object from host %s", self.net,
            conf.HOST_0_NAME
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )

        testflow.step(
            "Remove the unmanaged network %s from host (BOND) %s", self.net,
            conf.HOST_0_NAME
        )
        assert hl_host_network.clean_host_interfaces(conf.HOST_0_NAME)


@attr(tier=2)
@pytest.mark.usefixtures(
    create_network_in_dc_and_cluster.__name__,
    setup_networks_fixture.__name__,
    remove_network.__name__
)
class TestHostNetworkApiSetupNetworks05(NetworkTest):
    """
    1. Create network on DC/Cluster/Host
    2. Remove the network from DC
    3. Remove the unmanaged network from host
    """
    __test__ = True
    net = "unman_sn_05"
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net
            }
        }
    }

    @polarion("RHEVM3-12164")
    def test_remove_unmanaged_network(self):
        """
        Remove the unmanaged network from host
        """
        testflow.step(
            "Get unmanaged network %s object from host %s", self.net,
            conf.HOST_0_NAME
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[self.net]
        )

        testflow.step(
            "Remove the unmanaged network %s from host %s",
            self.net, conf.HOST_0_NAME
        )
        assert hl_host_network.clean_host_interfaces(conf.HOST_0_NAME)


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiSetupNetworks06(NetworkTest):
    """
    Attach VM network to host NIC that has VLAN network on it
    Attach VLAN network to host NIC that has VM network on it
    Attach VLAN network and VM network to same host NIC
    """
    __test__ = True
    net_1 = net_api_conf.SN_NETS[6][0]
    net_2 = net_api_conf.SN_NETS[6][1]
    net_case_vlan = net_api_conf.SN_NETS[6][2]
    net_case_vm = net_api_conf.SN_NETS[6][3]
    net_case_new_vm = net_api_conf.SN_NETS[6][4]
    net_case_new_vlan = net_api_conf.SN_NETS[6][5]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 2,
                "network": net_2
            }
        }
    }

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
        testflow.step(
            "Attach VLAN network %s to host NIC %s that has VM network %s "
            "on it", self.net_case_vlan, conf.HOST_0_NICS[1], self.net_1
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

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
        testflow.step(
            "Attach VM network %s to host NIC %s that has VLAN network %s "
            "on it", self.net_case_vm, conf.HOST_0_NICS[2], self.net_2
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

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
        testflow.step(
            "Attach VLAN network %s and VM network %s to same host NIC %s",
            self.net_case_new_vlan, self.net_case_new_vlan, conf.HOST_0_NICS[3]
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiSetupNetworks07(NetworkTest):
    """
    Attach VM network to BOND that has VLAN network on it
    Attach VLAN network to BOND that has VM network on it
    Attach VLAN network and VM network to same BOND
    """
    __test__ = True
    net_case_pre_vm = net_api_conf.SN_NETS[7][0]
    net_case_pre_vlan = net_api_conf.SN_NETS[7][1]
    net_case_vlan = net_api_conf.SN_NETS[7][2]
    net_case_vm = net_api_conf.SN_NETS[7][3]
    net_case_new_vm = net_api_conf.SN_NETS[7][4]
    net_case_new_vlan = net_api_conf.SN_NETS[7][5]
    bond_1 = "bond071"
    bond_2 = "bond072"
    bond_3 = "bond073"
    dummys_1 = net_api_conf.DUMMYS[:2]
    dummys_2 = net_api_conf.DUMMYS[2:4]
    dummys_3 = net_api_conf.DUMMYS[4:6]
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4]
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-5, -6]
            },
            net_case_pre_vm: {
                "nic": bond_1,
                "network": net_case_pre_vm
            },
            net_case_pre_vlan: {
                "nic": bond_2,
                "network": net_case_pre_vlan
            },
        }
    }

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
        testflow.step(
            "Attach VLAN network %s to BOND %s that has VM network %s on it",
            self.net_case_vlan, self.bond_1, self.net_case_pre_vm
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

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
        testflow.step(
            "Attach VM network %s to BOND %s that has VLAN network %s on it",
            self.net_case_vm, self.bond_2, self.net_case_pre_vlan
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

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
        testflow.step(
            "Attach VLAN network %s and VM network %s to same BOND %s",
            self.net_case_new_vlan, self.net_case_new_vm, self.bond_3
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
