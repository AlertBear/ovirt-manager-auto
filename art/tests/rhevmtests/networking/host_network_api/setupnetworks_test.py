#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API via SetupNetworks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as net_api_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, clean_host_interfaces, setup_networks_fixture
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
        testflow.teardown("Remove networks")
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Create networks: %s", net_api_conf.SN_DICT.keys())
    network_helper.prepare_networks_on_setup(
        networks_dict=net_api_conf.SN_DICT, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiSetupNetworks01(NetworkTest):
    """
    1) Attach multiple VLANs to host NIC.
    2) Attach multiple VLANs to BOND.
    """
    net_1 = net_api_conf.SN_NETS[1][0]
    net_2 = net_api_conf.SN_NETS[1][1]
    net_3 = net_api_conf.SN_NETS[1][2]
    net_4 = net_api_conf.SN_NETS[1][3]
    net_5 = net_api_conf.SN_NETS[1][4]
    net_6 = net_api_conf.SN_NETS[1][5]
    on_nic = [net_1, net_2, net_3]
    on_bond = [net_4, net_5, net_6]
    bond_1 = "bond01"

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            }
        }
    }

    @pytest.mark.parametrize(
        ("networks", "nic"),
        [
            polarion("RHEVM3-9823")([on_nic, 1]),
            polarion("RHEVM3-9824")([on_bond, bond_1]),
        ]
    )
    def test_multiple_vlans_networks_on_nic(self, networks, nic):
        """
        Attach multiple VLANs to host NIC
        Attach multiple VLANs to BOND
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        sn_dict = {
            "add": dict()
        }
        for net in networks:
            sn_dict["add"][net] = {
                "network": net,
                "nic": host_nic
            }

        testflow.step(
            "Attach multiple VLANs %s to host NIC %s", networks, host_nic
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
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
    """
    # test_01_create_bond params
    # test_02_update_bond_add_slave params
    # test_03_update_bond_remove_slave params
    # test_06_update_bond_mode params
    # test_07_update_bond_with_ip params
    bond_1 = "bond021"
    dummy_1 = [net_api_conf.DUMMYS[2]]

    # test_07_update_bond_with_ip params
    ip_netmask_net_1 = net_api_conf.IPS[22]
    net_1 = net_api_conf.SN_NETS[2][0]

    # test_08_create_bonds params
    # test_09_label_on_bond params
    dummys_1 = net_api_conf.DUMMYS[:2]
    dummys_2 = net_api_conf.DUMMYS[2:4]
    dummys_3 = net_api_conf.DUMMYS[4:6]
    dummys_4 = net_api_conf.DUMMYS[6:8]
    bond_2 = "bond022"
    bond_3 = "bond023"
    bond_4 = "bond024"

    # test_09_label_on_bond params
    label_1 = conf.LABEL_LIST[0]

    # test_10_create_bond_with_5_slaves params
    bond_5 = "bond025"
    dummys_5 = net_api_conf.DUMMYS[8:12]

    # clean_host_interfaces params
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


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiSetupNetworks03(NetworkTest):
    """
    1) Attach VLAN network and VM network to same host NIC
    2) Attach VLAN network and VM network to same BOND
    """
    net_1 = net_api_conf.SN_NETS[3][0]
    net_2 = net_api_conf.SN_NETS[3][1]
    net_3 = net_api_conf.SN_NETS[3][2]
    net_4 = net_api_conf.SN_NETS[3][3]
    on_nic = [net_1, net_2]
    on_bond = [net_3, net_4]
    bond_1 = "bond03"

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            }
        }
    }

    @pytest.mark.parametrize(
        ("networks", "nic"),
        [
            polarion("RHEVM3-14017")([on_nic, 1]),
            polarion("RHEVM3-14020")([on_bond, bond_1]),
        ]
    )
    @polarion("RHEVM3-14017")
    def test_attach_vm_and_vlan_network_to_nic(self, networks, nic):
        """
        Attach VLAN network and VM network to same host NIC
        Attach VLAN network and VM network to same BOND
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        sn_dict = {
            "add": dict()
        }
        for net in networks:
            sn_dict["add"][net] = {
                "network": net,
                "nic": host_nic
            }

        testflow.step(
            "Attach VLAN and VM network (%s) to same host NIC %s",
            networks, host_nic
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestHostNetworkApiSetupNetworks04(NetworkTest):
    """
    1) Attach network with static ipv4 and static ipv6 to host NIC.
    2) Attach Non-VM network with static ipv4 and static ipv6 to host NIC.
    3) Attach VLAN network with static ipv4 and static ipv6 to host NIC.
    4) Attach network with static ipv4 and static ipv6 to bond.
    """
    net_1 = net_api_conf.SN_NETS[4][0]
    ip_v6_1 = net_api_conf.IPV6_IPS[0]
    ip_v4_1 = net_api_conf.IPS[0]
    net_2 = net_api_conf.SN_NETS[4][1]
    ip_v6_2 = net_api_conf.IPV6_IPS[1]
    ip_v4_2 = net_api_conf.IPS[1]
    net_3 = net_api_conf.SN_NETS[4][2]
    ip_v6_3 = net_api_conf.IPV6_IPS[2]
    ip_v4_3 = net_api_conf.IPS[2]
    net_4 = net_api_conf.SN_NETS[4][3]
    ip_v6_4 = net_api_conf.IPV6_IPS[3]
    ip_v4_4 = net_api_conf.IPS[3]
    bond_1 = "bond041"

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            }
        }
    }

    @pytest.mark.parametrize(
        ("network", "nic", "ipv4", "ipv6"),
        [
            polarion("RHEVM3-17559")([net_1, 1, ip_v4_1, ip_v6_1]),
            polarion("RHEVM3-17560")([net_2, 2, ip_v4_2, ip_v6_2]),
            polarion("RHEVM3-17561")([net_3, 3, ip_v4_3, ip_v6_3]),
            polarion("RHEVM3-17562")([net_4, bond_1, ip_v4_4, ip_v6_4]),
        ]
    )
    def test_attach_network_with_ipv4_and_ipv6_to_nic(
        self, network, nic, ipv4, ipv6
    ):
        """
        Attach network with ipv4 and ipv6 to host NIC.
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        net_api_conf.BASIC_IPV4_AND_IPV6_DICT["ipv4"]["address"] = ipv4
        net_api_conf.BASIC_IPV4_AND_IPV6_DICT["ipv6"]["address"] = ipv6

        network_host_api_dict = {
            "add": {
                "1": {
                    "network": network,
                    "ip": net_api_conf.BASIC_IPV4_AND_IPV6_DICT,
                    "nic": host_nic
                },
            }
        }
        testflow.step(
            "Attach network %s with static IPv4 and IPv6 %s to host NIC %s",
            network, net_api_conf.BASIC_IPV4_AND_IPV6_DICT, host_nic
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
