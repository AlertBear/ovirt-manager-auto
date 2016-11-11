#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import config as net_api_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    update_host_to_another_cluster, manage_ip_and_refresh_capabilities
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, NetworkFixtures, clean_host_interfaces
)  # flake8: noqa


@pytest.fixture(scope="module", autouse=True)
def sync_prepare_setup(request):
    """
    Prepare setup for sync tests
    """
    network_api = NetworkFixtures()

    def fin3():
        """
        Activate host
        """
        assert ll_hosts.activate_host(
            positive=True, host=network_api.host_0_name
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove networks
        """
        assert hl_networks.remove_net_from_setup(
            host=network_api.host_0_name, all_net=True,
            mgmt_network=network_api.mgmt_bridge, data_center=network_api.dc_0
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove basic setup
        """
        assert hl_networks.remove_basic_setup(
            datacenter=net_api_conf.SYNC_DC, cluster=net_api_conf.SYNC_CL
        )
    request.addfinalizer(fin1)

    assert hl_networks.create_basic_setup(
        datacenter=net_api_conf.SYNC_DC, version=conf.COMP_VERSION,
        cluster=net_api_conf.SYNC_CL, cpu=conf.CPU_NAME
    )
    for networks_dict, dc, cl, in (
        (net_api_conf.SYNC_DICT_1, network_api.dc_0, network_api.cluster_0),
        (net_api_conf.SYNC_DICT_2, net_api_conf.SYNC_DC, net_api_conf.SYNC_CL)
    ):
        network_helper.prepare_networks_on_setup(
            networks_dict=networks_dict, dc=dc, cluster=cl
        )

    assert ll_hosts.deactivate_host(positive=True, host=network_api.host_0_name)


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync01(NetworkTest):
    """
    1) Check sync/un-sync different VLAN networks and sync the network.
    2) Check sync/un-sync different MTU networks over NIC and sync the network.
    3) Check sync/un-sync for VM/Non-VM networks over NIC and sync the network.
    4) Check sync/un-sync for VLAN/MTU/Bridge on the same network over NIC and
        sync the network.

    """
    __test__ = True
    net_case_1 = net_api_conf.SYNC_NETS_DC_1[1][0]
    net_case_1_vlan_id_actual = net_api_conf.VLAN_IDS[36]
    net_case_1_vlan_id_expected = net_api_conf.VLAN_IDS[40]
    net_case_2 = net_api_conf.SYNC_NETS_DC_1[1][1]
    net_case_2_vlan_id_actual = net_api_conf.VLAN_IDS[37]
    net_case_2_vlan_id_expected = None
    net_case_3 = net_api_conf.SYNC_NETS_DC_1[1][2]
    net_case_3_vlan_id_actual = None
    net_case_3_vlan_id_expected = net_api_conf.VLAN_IDS[41]
    net_case_4 = net_api_conf.SYNC_NETS_DC_1[1][3]
    net_case_4_mtu_actual = str(conf.MTU[0])
    net_case_4_mtu_expected = str(conf.MTU[1])
    net_case_5 = net_api_conf.SYNC_NETS_DC_1[1][4]
    net_case_5_mtu_actual = str(conf.MTU[1])
    net_case_5_mtu_expected = str(conf.MTU[3])
    net_case_6 = net_api_conf.SYNC_NETS_DC_1[1][5]
    net_case_6_mtu_actual = str(conf.MTU[3])
    net_case_6_mtu_expected = str(conf.MTU[0])
    net_case_7 = net_api_conf.SYNC_NETS_DC_1[1][6]
    net_case_7_bridge_actual = "true"
    net_case_7_bridge_expected = "false"
    net_case_8 = net_api_conf.SYNC_NETS_DC_1[1][7]
    net_case_8_bridge_actual = "false"
    net_case_8_bridge_expected = "true"
    net_case_9 = net_api_conf.SYNC_NETS_DC_1[1][8]
    net_case_9_vlan_id_actual = None
    net_case_9_mtu_actual = str(conf.MTU[0])
    net_case_9_bridge_actual = "false"
    net_case_9_vlan_id_expected = net_api_conf.VLAN_IDS[54]
    net_case_9_mtu_expected = str(conf.MTU[1])
    net_case_9_bridge_expected = "true"
    hosts_nets_nic_dict = {
        0: {
            net_case_1: {
                "nic": 1,
                "network": net_case_1,
                "datacenter": conf.DC_0
            },
            net_case_2: {
                "nic": 2,
                "network": net_case_2,
                "datacenter": conf.DC_0
            },
            net_case_3: {
                "nic": 3,
                "network": net_case_3,
                "datacenter": conf.DC_0
            },
            net_case_4: {
                "nic": 4,
                "network": net_case_4,
                "datacenter": conf.DC_0
            },
            net_case_5: {
                "nic": 5,
                "network": net_case_5,
                "datacenter": conf.DC_0
            },
            net_case_6: {
                "nic": 6,
                "network": net_case_6,
                "datacenter": conf.DC_0
            },
            net_case_7: {
                "nic": 7,
                "network": net_case_7,
                "datacenter": conf.DC_0
            },
            net_case_8: {
                "nic": 8,
                "network": net_case_8,
                "datacenter": conf.DC_0
            },
            net_case_9: {
                "nic": 9,
                "network": net_case_9,
                "datacenter": conf.DC_0
            },

        }
    }

    @polarion("RHEVM3-13977")
    def test_01_unsync_network_change_vlan(self):
        """
        Check that the network is un-sync and the sync reason is different VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different VLAN %s", self.net_case_1, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-13979")
    def test_02_unsync_network_vlan_to_no_vlan(self):
        """
        Check that the network is un-sync and the sync reason is no VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_2_vlan_id_expected,
                    "actual": self.net_case_2_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is no "
            "VLAN %s", self.net_case_2, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s")
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-13980")
    def test_03_unsync_network_no_vlan_to_vlan(self):
        """
        Check that the network is un-sync and the sync reason is VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_3_vlan_id_expected,
                    "actual": self.net_case_3_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "VLAN %s", self.net_case_3, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )

    @polarion("RHEVM3-13987")
    def test_04_unsync_network_change_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_4: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_4_mtu_expected,
                    "actual": self.net_case_4_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU %s", self.net_case_4, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_4)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_4]
        )

    @polarion("RHEVM3-13988")
    def test_05_unsync_network_mtu_to_no_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_5: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_5_mtu_expected,
                    "actual": self.net_case_5_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU %s", self.net_case_5, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_5)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_5]
        )

    @polarion("RHEVM3-13989")
    def test_06_unsync_network_no_mtu_to_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_6: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_6_mtu_expected,
                    "actual": self.net_case_6_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU %s", self.net_case_6, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_6)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_6]
        )

    @polarion("RHEVM3-13993")
    def test_07_unsync_network_change_vm_non_vm(self):
        """
        Check that the network is un-sync and the sync reason is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_7: {
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_7_bridge_expected,
                    "actual": self.net_case_7_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "Vm/Non-VM %s", self.net_case_7, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_7)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_7]
        )

    @polarion("RHEVM3-13994")
    def test_08_unsync_network_non_vm_vm(self):
        """
        Check that the network is un-sync and the sync reason is is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_8: {
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_8_bridge_expected,
                    "actual": self.net_case_8_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is is "
            "Vm/Non-VM %s", self.net_case_8, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_8)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_8]
        )

    @polarion("RHEVM3-13997")
    def test_09_unsync_network_change_vlan_mtu_bridge(self):
        """
        Check that the network is un-sync and the sync reasons are different
        VLAN, MTU and Bridge
        Sync the network
        """
        compare_dict = {
            self.net_case_9: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_9_vlan_id_expected,
                    "actual": self.net_case_9_vlan_id_actual
                },
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_9_mtu_expected,
                    "actual": self.net_case_9_mtu_actual
                },
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_9_bridge_expected,
                    "actual": self.net_case_9_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons are "
            "different VLAN, MTU and Bridge %s", self.net_case_9, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_9)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_9]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync02(NetworkTest):
    """
    1) Check sync/un-sync different VLAN networks over BOND and,
        sync the network.
    2) Check sync/un-sync different MTU networks over BOND and,
        sync the network.
    3) Check sync/un-sync for VM/Non-VM networks over BOND and,
        sync the network.
    4) Check sync/un-sync for VLAN/MTU/Bridge on the same network over BOND,
        and sync the network.

    """
    __test__ = True
    bond_1 = "bond021"
    net_case_1 = net_api_conf.SYNC_NETS_DC_1[2][0]
    net_case_1_vlan_id_actual = net_api_conf.VLAN_IDS[42]
    bond_2 = "bond022"
    net_case_1_vlan_id_expected = net_api_conf.VLAN_IDS[44]
    net_case_2 = net_api_conf.SYNC_NETS_DC_1[2][1]
    net_case_2_vlan_id_actual = net_api_conf.VLAN_IDS[43]
    net_case_2_vlan_id_expected = None
    bond_3 = "bond023"
    net_case_3 = net_api_conf.SYNC_NETS_DC_1[2][2]
    net_case_3_vlan_id_actual = None
    net_case_3_vlan_id_expected = net_api_conf.VLAN_IDS[45]
    bond_4 = "bond024"
    net_case_4 = net_api_conf.SYNC_NETS_DC_1[2][3]
    net_case_4_mtu_actual = str(conf.MTU[0])
    net_case_4_mtu_expected = str(conf.MTU[1])
    bond_5 = "bond025"
    net_case_5 = net_api_conf.SYNC_NETS_DC_1[2][4]
    net_case_5_mtu_actual = str(conf.MTU[1])
    net_case_5_mtu_expected = str(conf.MTU[3])
    bond_6 = "bond026"
    net_case_6 = net_api_conf.SYNC_NETS_DC_1[2][5]
    net_case_6_mtu_actual = str(conf.MTU[3])
    net_case_6_mtu_expected = str(conf.MTU[0])
    bond_7 = "bond027"
    net_case_7 = net_api_conf.SYNC_NETS_DC_1[2][6]
    net_case_7_bridge_actual = "true"
    net_case_7_bridge_expected = "false"
    net_case_8 = net_api_conf.SYNC_NETS_DC_1[2][7]
    net_case_8_bridge_actual = "false"
    net_case_8_bridge_expected = "true"
    bond_8 = "bond028"
    net_case_9 = net_api_conf.SYNC_NETS_DC_1[2][8]
    net_case_9_vlan_id_actual = None
    net_case_9_mtu_actual = str(conf.MTU[0])
    net_case_9_bridge_actual = "false"
    net_case_9_vlan_id_expected = net_api_conf.VLAN_IDS[55]
    net_case_9_mtu_expected = str(conf.MTU[1])
    net_case_9_bridge_expected = "true"
    bond_9 = "bond029"
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
            net_case_1: {
                "nic": bond_1,
                "network": net_case_1,
                "datacenter": conf.DC_0
            },
            net_case_2: {
                "nic": bond_2,
                "network": net_case_2,
                "datacenter": conf.DC_0
            },
            net_case_3: {
                "nic": bond_3,
                "network": net_case_3,
                "datacenter": conf.DC_0
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [-7, -8]
            },
            bond_5: {
                "nic": bond_5,
                "slaves": [-9, -10]
            },
            bond_6: {
                "nic": bond_6,
                "slaves": [-11, -12]
            },
            net_case_4: {
                "nic": bond_4,
                "network": net_case_4,
                "datacenter": conf.DC_0
            },
            net_case_5: {
                "nic": bond_5,
                "network": net_case_5,
                "datacenter": conf.DC_0
            },
            net_case_6: {
                "nic": bond_6,
                "network": net_case_6,
                "datacenter": conf.DC_0
            },
            bond_7: {
                "nic": bond_7,
                "slaves": [-13, -14]
            },
            bond_8: {
                "nic": bond_8,
                "slaves": [-15, -16]
            },
            net_case_7: {
                "nic": bond_7,
                "network": net_case_7,
                "datacenter": conf.DC_0
            },
            net_case_8: {
                "nic": bond_8,
                "network": net_case_8,
                "datacenter": conf.DC_0
            },
            bond_9: {
                "nic": bond_9,
                "slaves": [-17, -18]
            },
            net_case_9: {
                "nic": bond_9,
                "network": net_case_9,
                "datacenter": conf.DC_0
            },
        }
    }

    @polarion("RHEVM3-13981")
    def test_01_unsync_network_change_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different VLAN
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different VLAN over BOND %s", self.net_case_1, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-13982")
    def test_02_unsync_network_vlan_to_no_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is no VLAN
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_2_vlan_id_expected,
                    "actual": self.net_case_2_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is no "
            "VLAN over BOND %s", self.net_case_2, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_2)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-13985")
    def test_03_unsync_network_no_vlan_to_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is VLAN over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_3_vlan_id_expected,
                    "actual": self.net_case_3_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is VLAN "
            "over BOND %s", self.net_case_3, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )

    @polarion("RHEVM3-13990")
    def test_04_unsync_network_change_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_4: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_4_mtu_expected,
                    "actual": self.net_case_4_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU over BOND %s", self.net_case_4,  compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_4)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_4]
        )

    @polarion("RHEVM3-13991")
    def test_05_unsync_network_mtu_to_no_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_5: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_5_mtu_expected,
                    "actual": self.net_case_5_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU over BOND %s", self.net_case_5, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_5)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_5]
        )

    @polarion("RHEVM3-13992")
    def test_06_unsync_network_no_mtu_to_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different
        MTU over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_6: {
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_6_mtu_expected,
                    "actual": self.net_case_6_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "different MTU over BOND %s", self.net_case_6, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_6)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_6]
        )

    @polarion("RHEVM3-13995")
    def test_07_unsync_network_change_vm_non_vm_bond(self):
        """
        Check that the network is un-sync and the sync reason is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_7: {
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_7_bridge_expected,
                    "actual": self.net_case_7_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "Vm/Non-VM %s", self.net_case_7, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_7)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_7]
        )

    @polarion("RHEVM3-13996")
    def test_08_unsync_network_non_vm_vm_bond(self):
        """
        Check that the network is un-sync and the sync reason is is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_8: {
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_8_bridge_expected,
                    "actual": self.net_case_8_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is is "
            "Vm/Non-VM %s", self.net_case_8, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_8)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_8]
        )

    @polarion("RHEVM3-13998")
    def test_09_unsync_network_change_vlan_mtu_bridge(self):
        """
        Check that the network is un-sync and the sync reasons are different
        VLAN, MTU and Bridge
        Sync the network
        """
        compare_dict = {
            self.net_case_9: {
                net_api_conf.VLAN_STR: {
                    "expected": self.net_case_9_vlan_id_expected,
                    "actual": self.net_case_9_vlan_id_actual
                },
                net_api_conf.MTU_STR: {
                    "expected": self.net_case_9_mtu_expected,
                    "actual": self.net_case_9_mtu_actual
                },
                net_api_conf.BRIDGE_STR: {
                    "expected": self.net_case_9_bridge_expected,
                    "actual": self.net_case_9_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons are "
            "different VLAN, MTU and Bridge %s", self.net_case_9, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_case_9)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_9]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    manage_ip_and_refresh_capabilities.__name__,

)
class TestHostNetworkApiSync03(NetworkTest):
    """
    1) Check sync/un-sync for changed IP and sync the network.
    2) Check sync/un-sync for changed netmask and sync the network.
    3) Check sync/un-sync for changed netmask prefix and sync the network.
    4) Check sync/un-sync for no-IP to IP and sync the network.
    5) Check sync/un-sync for removed IP and sync the network.
    """
    __test__ = True
    SYNC_IPS = network_helper.create_random_ips(num_of_ips=4, mask=24)

    # Test 01 parameters
    ip_netmask_net_1 = SYNC_IPS[0]
    net_1 = net_api_conf.SYNC_NETS_DC_1[3][0]
    net_case_1_ip_expected = ip_netmask_net_1
    actual_ip_net_1 = "10.10.10.10"

    # Test 02 parameters
    net_2 = net_api_conf.SYNC_NETS_DC_1[3][1]
    net_case_2_netmask_expected = net_api_conf.IP_DICT_NETMASK["netmask"]
    actual_netmask_net_2 = "255.255.255.255"
    ip_netmask_net_2 = SYNC_IPS[1]

    # Test 03 parameters
    net_3 = net_api_conf.SYNC_NETS_DC_1[3][2]
    net_case_3_netmask_prefix_expected = net_api_conf.IP_DICT_PREFIX["netmask"]
    actual_netmask_net_3 = "255.255.255.255"
    ip_prefix_net_3 = SYNC_IPS[2]

    # Test 04 parameters
    net_4 = net_api_conf.SYNC_NETS_DC_1[3][3]
    actual_ip_net_4 = "10.10.10.11"
    net_case_4_boot_proto_expected = "NONE"
    net_case_4_boot_proto_actual = "STATIC_IP"

    # Test 05 parameters
    net_5 = net_api_conf.SYNC_NETS_DC_1[3][4]
    net_case_5_boot_proto_expected = "STATIC_IP"
    net_case_5_boot_proto_actual = "NONE"
    ip_netmask_net_5 = SYNC_IPS[3]

    manage_ip_list = [
        (net_1, actual_ip_net_1, None, True),
        (net_2, None, actual_netmask_net_2, True),
        (net_3, None, actual_netmask_net_3, True),
        (net_4, actual_ip_net_4, None, True),
        (net_5, None, None, False)
    ]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "ip": {
                    "1": {
                        "address": ip_netmask_net_1,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "ip": {
                    "1": {
                        "address": ip_netmask_net_2,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            net_3: {
                "nic": 3,
                "network": net_3,
                "ip": {
                    "1": {
                        "address": ip_prefix_net_3
                    }
                }
            },
            net_4: {
                "nic": 4,
                "network": net_4,
            },
            net_5: {
                "nic": 5,
                "network": net_5,
                "ip": {
                    "1": {
                        "address": ip_netmask_net_5,
                        "netmask": "255.255.255.0",
                    }
                }
            },
        }
    }

    @polarion("RHEVM3-13999")
    def test_01_unsync_network_change_ip(self):
        """
        Check that the network is un-sync and the sync reasons is changed IP
        Sync the network
        """
        compare_dict = {
            self.net_1: {
                net_api_conf.IPADDR_STR: {
                    "expected": self.net_case_1_ip_expected,
                    "actual": self.actual_ip_net_1
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons is "
            "changed IP %s", self.net_1, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_1]
        )

    @polarion("RHEVM3-14000")
    def test_02_unsync_network_change_netmask(self):
        """
        Check that the network is un-sync and the sync reason is changed
        netmask
        Sync the network
        """
        compare_dict = {
            self.net_2: {
                net_api_conf.NETMASK_STR: {
                    "expected": self.net_case_2_netmask_expected,
                    "actual": self.actual_netmask_net_2
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "changed netmask %s", self.net_2, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_2)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_2]
        )

    @polarion("RHEVM3-14001")
    def test_03_unsync_network_change_netmask_prefix(self):
        """
        Check that the network is un-sync and the sync reasons is changed
        netmask prefix
        Sync the network
        """
        compare_dict = {
            self.net_3: {
                net_api_conf.NETMASK_STR: {
                    "expected": self.net_case_3_netmask_prefix_expected,
                    "actual": self.actual_netmask_net_3
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons is "
            "changed netmask prefix %s", self.net_3, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_3]
        )

    @polarion("RHEVM3-14009")
    def test_04_unsync_network_no_ip_to_ip(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
        Sync the network
        """
        compare_dict = {
            self.net_4: {
                net_api_conf.BOOTPROTO_STR: {
                    "expected": self.net_case_4_boot_proto_expected,
                    "actual": self.net_case_4_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons "
            "is new IP %s", self.net_4, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_4)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_4]
        )

    @polarion("RHEVM3-14011")
    def test_05_unsync_network_remove_ip(self):
        """
        Check that the network is un-sync and the sync reasons is no IP
        Sync the network
        """
        compare_dict = {
            self.net_5: {
                net_api_conf.BOOTPROTO_STR: {
                    "expected": self.net_case_5_boot_proto_expected,
                    "actual": self.net_case_5_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons "
            "is no IP %s", self.net_5, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_5)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_5]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    manage_ip_and_refresh_capabilities.__name__
)
class TestHostNetworkApiSync04(NetworkTest):
    """
    1) Check sync/un-sync for changed IP over BOND and sync the network.
    2) Check sync/un-sync for changed netmask over BOND and sync the network.
    3) Check sync/un-sync for changed netmask prefix over BOND.
    4) Check sync/un-sync for no-IP to IP over BOND and sync the network.
    5) Check sync/un-sync for removed IP over BOND and sync the network.
    """
    __test__ = True
    SYNC_IPS = network_helper.create_random_ips(num_of_ips=4, mask=24)

    # Test 01 parameters
    ip_netmask_net_1 = SYNC_IPS[0]
    net_1 = net_api_conf.SYNC_NETS_DC_1[4][0]
    net_case_1_ip_expected = ip_netmask_net_1
    actual_ip_net_1 = "10.10.10.12"
    bond_1 = "bond041"

    # Test 02 parameters
    net_2 = net_api_conf.SYNC_NETS_DC_1[4][1]
    net_case_2_netmask_expected = net_api_conf.IP_DICT_NETMASK["netmask"]
    actual_netmask_net_2 = "255.255.255.255"
    bond_2 = "bond042"
    ip_netmask_net_2 = SYNC_IPS[1]

    # Test 03 parameters
    net_3 = net_api_conf.SYNC_NETS_DC_1[4][2]
    net_case_3_netmask_prefix_expected = net_api_conf.IP_DICT_PREFIX["netmask"]
    actual_netmask_net_3 = "255.255.255.255"
    bond_3 = "bond043"
    ip_prefix_net_3 = SYNC_IPS[2]

    # Test 04 parameters
    net_4 = net_api_conf.SYNC_NETS_DC_1[4][3]
    actual_ip_net_4 = "10.10.10.13"
    net_case_4_boot_proto_expected = "NONE"
    net_case_4_boot_proto_actual = "STATIC_IP"
    bond_4 = "bond044"

    # Test 05 parameters
    set_ip = False
    net_5 = net_api_conf.SYNC_NETS_DC_1[4][4]
    net_case_5_boot_proto_expected = "STATIC_IP"
    net_case_5_boot_proto_actual = "NONE"
    bond_5 = "bond045"
    ip_netmask_5 = SYNC_IPS[3]

    manage_ip_list = [
        (net_1, actual_ip_net_1, None, True),
        (net_2, None, actual_netmask_net_2, True),
        (net_3, None, actual_netmask_net_3, True),
        (net_4, actual_ip_net_4, None, True),
        (net_5, None, None, False)
    ]

    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2]
            },
            net_1: {
                "nic": bond_1,
                "network": net_1,
                "ip": {
                    "1": {
                        "address": ip_netmask_net_1,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4]
            },
            net_2: {
                "nic": bond_2,
                "network": net_2,
                "ip": {
                    "1": {
                        "address": ip_netmask_net_2,
                        "netmask": "255.255.255.0",
                    }
                }
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-5, -6]
            },
            net_3: {
                "nic": bond_3,
                "network": net_3,
                "ip": {
                    "1": {
                        "address": ip_prefix_net_3,
                    }
                }
            },
            bond_4: {
                "nic": bond_4,
                "slaves": [-7, -8]
            },
            net_4: {
                "nic": bond_4,
                "network": net_4,
            },
            bond_5: {
                "nic": bond_5,
                "slaves": [-9, 10]
            },
            net_5: {
                "nic": bond_5,
                "network": net_5,
                "ip": {
                    "1": {
                        "address": ip_netmask_5,
                        "netmask": "255.255.255.0",
                    }
                }
            }
        }
    }

    @polarion("RHEVM3-14002")
    def test_01_unsync_network_change_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is changed IP
        Sync the network
        """
        compare_dict = {
            self.net_1: {
                net_api_conf.IPADDR_STR: {
                    "expected": self.net_case_1_ip_expected,
                    "actual": self.actual_ip_net_1
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons is "
            "changed IP %s", self.net_1, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_1]
        )

    @polarion("RHEVM3-14003")
    def test_02_unsync_network_change_netmask_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is changed
        netmask
        Sync the network
        """
        compare_dict = {
            self.net_2: {
                net_api_conf.NETMASK_STR: {
                    "expected": self.net_case_2_netmask_expected,
                    "actual": self.actual_netmask_net_2
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reason is "
            "changed netmask %s", self.net_2, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_2)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_2]
        )

    @polarion("RHEVM3-14004")
    def test_03_unsync_network_change_netmask_prefix_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is changed
        netmask prefix
        Sync the network
        """
        compare_dict = {
            self.net_3: {
                net_api_conf.NETMASK_STR: {
                    "expected": self.net_case_3_netmask_prefix_expected,
                    "actual": self.actual_netmask_net_3
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons is "
            "changed netmask prefix %s", self.net_3, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_3]
        )

    @polarion("RHEVM3-14010")
    def test_04_unsync_network_no_ip_to_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
        Sync the network
        """
        compare_dict = {
            self.net_4: {
                net_api_conf.BOOTPROTO_STR: {
                    "expected": self.net_case_4_boot_proto_expected,
                    "actual": self.net_case_4_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons "
            "is new IP %s", self.net_4, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_4)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_4]
        )

    @polarion("RHEVM3-14012")
    def test_05_unsync_network_remove_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is no IP
        Sync the network
        """
        compare_dict = {
            self.net_5: {
                net_api_conf.BOOTPROTO_STR: {
                    "expected": self.net_case_5_boot_proto_expected,
                    "actual": self.net_case_5_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network %s is un-sync and the sync reasons "
            "is no IP %s", self.net_5, compare_dict
        )
        assert helper.get_networks_sync_status_and_unsync_reason(compare_dict)

        testflow.step("Sync the network %s", self.net_5)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_5]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync05(NetworkTest):
    """
    Check sync/un-sync for:
     1. Changed QoS
     2. No QoS to QoS
     3. QoS to no QoS
    Sync the network
    """
    __test__ = True
    net_case_1 = net_api_conf.SYNC_NETS_DC_1[5][0]
    net_case_1_qos_expected = "20"
    net_case_1_qos_actual = "10"
    net_case_2 = net_api_conf.SYNC_NETS_DC_1[5][1]
    net_case_2_qos_expected = "10"
    net_case_2_qos_actual = None
    net_case_3 = net_api_conf.SYNC_NETS_DC_1[5][2]
    net_case_3_qos_expected = None
    net_case_3_qos_actual = "10"
    net_case_4_1 = net_api_conf.SYNC_NETS_DC_1[5][3]
    net_case_4_2 = net_api_conf.SYNC_NETS_DC_1[5][4]
    expected_actual_dict_1 = {
        "expected": net_case_1_qos_expected,
        "actual": net_case_1_qos_actual
    }
    expected_actual_dict_2 = {
        "expected": net_case_2_qos_expected,
        "actual": net_case_2_qos_actual
    }
    expected_actual_dict_3 = {
        "expected": net_case_3_qos_expected,
        "actual": net_case_3_qos_actual
    }
    hosts_nets_nic_dict = {
        0: {
            net_case_1: {
                "nic": 1,
                "network": net_case_1,
                "datacenter": conf.DC_0
            },
            net_case_2: {
                "nic": 2,
                "network": net_case_2,
                "datacenter": conf.DC_0
            },
            net_case_3: {
                "nic": 3,
                "network": net_case_3,
                "datacenter": conf.DC_0
            },
            net_case_4_1: {
                "nic": 4,
                "network": net_case_4_1,
                "datacenter": conf.DC_0
            },
            net_case_4_2: {
                "nic": 4,
                "network": net_case_4_2,
                "datacenter": conf.DC_0
            }
        }
    }

    @polarion("RHEVM3-14026")
    def test_unsync_network_change_qos(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons "
                "changed QoS %s", self.net_case_1, compare_dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-14027")
    def test_unsync_network_no_qos_to_qos(self):
        """
        Check that the network is un-sync and the sync reasons no QoS
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons"
                "no QoS %s", self.net_case_2, compare_dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_2)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-14028")
    def test_unsync_network_qos_to_no_qos(self):
        """
        Check that the network is un-sync and the sync reasons QoS
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons "
                "QoS %s", self.net_case_3, compare_dict_

            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )

    @polarion("RHEVM3-6538")
    def test_remove_qos_unsync_network(self):
        """
        1.  Remove host network QoS that is attached to the first network
            on the host
        2.  Check that the first network is unsynced
        3.  Remove host network QoS that is attached to the second network
            on the host
        4.  Check that the second network is unsynced
        5.  Sync both networks on the host
        """
        qos_names = net_api_conf.QOS_NAME[5][3:5]
        nets = [self.net_case_4_1, self.net_case_4_2]

        for qos_name, net in zip(qos_names, nets):
            testflow.step(
                "Removing QoS: %s from DC: %s", qos_name, net_api_conf.SYNC_DC
            )
            network_helper.remove_qos_from_dc(
                qos_name=qos_name, datacenter=net_api_conf.SYNC_DC
            )

            testflow.step("Check the network: %s is unsynced", net)
            assert not network_helper.networks_sync_status(
                host=conf.HOST_0_NAME, networks=[net]
            )

        testflow.step("Sync both networks")
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=nets
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_host_to_another_cluster.__name__
)
class TestHostNetworkApiSync06(NetworkTest):
    """
    Check sync/un-sync over BOND for:
     1. Changed QoS
     2. No QoS to QoS
     3. QoS to no QoS
    Sync the network
    """
    __test__ = True
    bond_1 = "bond201"
    bond_2 = "bond202"
    bond_3 = "bond203"
    net_case_1 = net_api_conf.SYNC_NETS_DC_1[6][0]
    net_case_1_qos_expected = "20"
    net_case_1_qos_actual = "10"
    net_case_2 = net_api_conf.SYNC_NETS_DC_1[6][1]
    net_case_2_qos_expected = "10"
    net_case_2_qos_actual = None
    net_case_3 = net_api_conf.SYNC_NETS_DC_1[6][2]
    net_case_3_qos_expected = None
    net_case_3_qos_actual = "10"
    expected_actual_dict_1 = {
        "expected": net_case_1_qos_expected,
        "actual": net_case_1_qos_actual
    }
    expected_actual_dict_2 = {
        "expected": net_case_2_qos_expected,
        "actual": net_case_2_qos_actual
    }
    expected_actual_dict_3 = {
        "expected": net_case_3_qos_expected,
        "actual": net_case_3_qos_actual
    }
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
            net_case_1: {
                "nic": bond_1,
                "network": net_case_1,
                "datacenter": conf.DC_0
            },
            net_case_2: {
                "nic": bond_2,
                "network": net_case_2,
                "datacenter": conf.DC_0
            },
            net_case_3: {
                "nic": bond_3,
                "network": net_case_3,
                "datacenter": conf.DC_0
            },

        }
    }

    @polarion("RHEVM3-14029")
    def test_unsync_network_change_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        over BOND
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons"
                "changed QoS over BOND %s", self.net_case_1, compare_dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_1)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-14030")
    def test_unsync_network_no_qos_to_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons no QoS over BOND
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons"
                "no QoS over BOND %s", self.net_case_2, compare_dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_2)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-14031")
    def test_unsync_network_qos_to_no_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons QoS over BOND
        Sync the network
        """
        for qos_value in net_api_conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }
            testflow.step(
                "Check that the network %s is un-sync and the sync reasons "
                "QoS over BOND %s", self.net_case_3, compare_dict_
            )
            assert helper.get_networks_sync_status_and_unsync_reason(
                compare_dict_
            )

        testflow.step("Sync the network %s", self.net_case_3)
        assert network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )
