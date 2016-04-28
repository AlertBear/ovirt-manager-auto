#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import logging

import config as conf
import helper
import pytest
import rhevmtests.networking.config as net_conf
import rhevmtests.networking.helper as network_helper
from _pytest_art.marks import tier2
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    sync_case_01, sync_case_02, sync_case_03, sync_case_04, sync_case_05,
    sync_case_06, sync_case_07, sync_case_08, sync_case_09, sync_case_10,
    sync_case_11, sync_case_12, sync_case_13, sync_case_14, sync_case_15,
    sync_case_16, sync_case_17, sync_case_18, sync_case_19, sync_case_20
)

logger = logging.getLogger("Host_Network_API_Sync_Cases")


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_01.__name__)
class TestHostNetworkApiSync01(NetworkTest):
    """
    Check sync/un-sync different VLAN networks
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[1][0]
    net_case_1_vlan_id_actual = conf.VLAN_IDS[36]
    net_case_1_vlan_id_expected = conf.VLAN_IDS[40]
    net_case_2 = conf.SYNC_NETS_DC_1[1][1]
    net_case_2_vlan_id_actual = conf.VLAN_IDS[37]
    net_case_2_vlan_id_expected = None
    net_case_3 = conf.SYNC_NETS_DC_1[1][2]
    net_case_3_vlan_id_actual = None
    net_case_3_vlan_id_expected = conf.VLAN_IDS[41]

    @polarion("RHEVM3-13977")
    def test_unsync_network_change_vlan(self):
        """
        Check that the network is un-sync and the sync reason is different VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different VLAN"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13979")
    def test_unsync_network_vlan_to_no_vlan(self):
        """
        Check that the network is un-sync and the sync reason is no VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.VLAN_STR: {
                    "expected": self.net_case_2_vlan_id_expected,
                    "actual": self.net_case_2_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is no "
            "VLAN"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-13980")
    def test_unsync_network_no_vlan_to_vlan(self):
        """
        Check that the network is un-sync and the sync reason is VLAN
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                conf.VLAN_STR: {
                    "expected": self.net_case_3_vlan_id_expected,
                    "actual": self.net_case_3_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is VLAN"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_02.__name__)
class TestHostNetworkApiSync02(NetworkTest):
    """
    Check sync/un-sync different VLAN networks over BOND
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[2][0]
    net_case_1_vlan_id_actual = conf.VLAN_IDS[42]
    net_case_1_vlan_id_expected = conf.VLAN_IDS[44]
    net_case_2 = conf.SYNC_NETS_DC_1[2][1]
    net_case_2_vlan_id_actual = conf.VLAN_IDS[43]
    net_case_2_vlan_id_expected = None
    net_case_3 = conf.SYNC_NETS_DC_1[2][2]
    net_case_3_vlan_id_actual = None
    net_case_3_vlan_id_expected = conf.VLAN_IDS[45]
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]
    dummys_3 = conf.DUMMYS[4:6]

    @polarion("RHEVM3-13981")
    def test_unsync_network_change_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different VLAN
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different VLAN over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13982")
    def test_unsync_network_vlan_to_no_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is no VLAN
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.VLAN_STR: {
                    "expected": self.net_case_2_vlan_id_expected,
                    "actual": self.net_case_2_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is no "
            "VLAN over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-13985")
    def test_unsync_network_no_vlan_to_vlan_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is VLAN over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                conf.VLAN_STR: {
                    "expected": self.net_case_3_vlan_id_expected,
                    "actual": self.net_case_3_vlan_id_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is VLAN "
            "over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_03.__name__)
class TestHostNetworkApiSync03(NetworkTest):
    """
    Check sync/un-sync different MTU networks over NIC
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[3][0]
    net_case_1_mtu_actual = str(net_conf.MTU[0])
    net_case_1_mtu_expected = str(net_conf.MTU[1])
    net_case_2 = conf.SYNC_NETS_DC_1[3][1]
    net_case_2_mtu_actual = str(net_conf.MTU[1])
    net_case_2_mtu_expected = str(net_conf.MTU[3])
    net_case_3 = conf.SYNC_NETS_DC_1[3][2]
    net_case_3_mtu_actual = str(net_conf.MTU[3])
    net_case_3_mtu_expected = str(net_conf.MTU[0])

    @polarion("RHEVM3-13987")
    def test_unsync_network_change_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.MTU_STR: {
                    "expected": self.net_case_1_mtu_expected,
                    "actual": self.net_case_1_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13988")
    def test_unsync_network_mtu_to_no_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.MTU_STR: {
                    "expected": self.net_case_2_mtu_expected,
                    "actual": self.net_case_2_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-13989")
    def test_unsync_network_no_mtu_to_mtu(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                conf.MTU_STR: {
                    "expected": self.net_case_3_mtu_expected,
                    "actual": self.net_case_3_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_04.__name__)
class TestHostNetworkApiSync04(NetworkTest):
    """
    Check sync/un-sync different MTU networks over BOND
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[4][0]
    net_case_1_mtu_actual = str(net_conf.MTU[0])
    net_case_1_mtu_expected = str(net_conf.MTU[1])
    net_case_2 = conf.SYNC_NETS_DC_1[4][1]
    net_case_2_mtu_actual = str(net_conf.MTU[1])
    net_case_2_mtu_expected = str(net_conf.MTU[3])
    net_case_3 = conf.SYNC_NETS_DC_1[4][2]
    net_case_3_mtu_actual = str(net_conf.MTU[3])
    net_case_3_mtu_expected = str(net_conf.MTU[0])
    bond_1 = "bond31"
    bond_2 = "bond32"
    bond_3 = "bond33"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]
    dummys_3 = conf.DUMMYS[4:6]

    @polarion("RHEVM3-13990")
    def test_unsync_network_change_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.MTU_STR: {
                    "expected": self.net_case_1_mtu_expected,
                    "actual": self.net_case_1_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13991")
    def test_unsync_network_mtu_to_no_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different MTU
        over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.MTU_STR: {
                    "expected": self.net_case_2_mtu_expected,
                    "actual": self.net_case_2_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-13992")
    def test_unsync_network_no_mtu_to_mtu_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is different
        MTU over BOND
        Sync the network
        """
        compare_dict = {
            self.net_case_3: {
                conf.MTU_STR: {
                    "expected": self.net_case_3_mtu_expected,
                    "actual": self.net_case_3_mtu_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "different MTU over BOND"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_05.__name__)
class TestHostNetworkApiSync05(NetworkTest):
    """
    Check sync/un-sync for VM/Non-VM networks over NIC
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[5][0]
    net_case_1_bridge_actual = "true"
    net_case_1_bridge_expected = "false"
    net_case_2 = conf.SYNC_NETS_DC_1[5][1]
    net_case_2_bridge_actual = "false"
    net_case_2_bridge_expected = "true"

    @polarion("RHEVM3-13993")
    def test_unsync_network_change_vm_non_vm(self):
        """
        Check that the network is un-sync and the sync reason is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BRIDGE_STR: {
                    "expected": self.net_case_1_bridge_expected,
                    "actual": self.net_case_1_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "Vm/Non-VM"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13994")
    def test_unsync_network_non_vm_vm(self):
        """
        Check that the network is un-sync and the sync reason is is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.BRIDGE_STR: {
                    "expected": self.net_case_2_bridge_expected,
                    "actual": self.net_case_2_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is is "
            "Vm/Non-VM"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_06.__name__)
class TestHostNetworkApiSync06(NetworkTest):
    """
    Check sync/un-sync for VM/Non-VM networks over BOND
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[6][0]
    net_case_1_bridge_actual = "true"
    net_case_1_bridge_expected = "false"
    net_case_2 = conf.SYNC_NETS_DC_1[6][1]
    net_case_2_bridge_actual = "false"
    net_case_2_bridge_expected = "true"
    bond_1 = "bond61"
    bond_2 = "bond62"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]

    @polarion("RHEVM3-13995")
    def test_unsync_network_change_vm_non_vm_bond(self):
        """
        Check that the network is un-sync and the sync reason is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BRIDGE_STR: {
                    "expected": self.net_case_1_bridge_expected,
                    "actual": self.net_case_1_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "Vm/Non-VM"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-13996")
    def test_unsync_network_non_vm_vm_bond(self):
        """
        Check that the network is un-sync and the sync reason is is Vm/Non-VM
        Sync the network
        """
        compare_dict = {
            self.net_case_2: {
                conf.BRIDGE_STR: {
                    "expected": self.net_case_2_bridge_expected,
                    "actual": self.net_case_2_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is is "
            "Vm/Non-VM"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_07.__name__)
class TestHostNetworkApiSync07(NetworkTest):
    """
    Check sync/un-sync for VLAN/MTU/Bridge on the same network
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[7][0]
    net_case_1_vlan_id_actual = None
    net_case_1_mtu_actual = str(net_conf.MTU[0])
    net_case_1_bridge_actual = "false"
    net_case_1_vlan_id_expected = conf.VLAN_IDS[54]
    net_case_1_mtu_expected = str(net_conf.MTU[1])
    net_case_1_bridge_expected = "true"

    @polarion("RHEVM3-13997")
    def test_unsync_network_change_vlan_mtu_bridge(self):
        """
        Check that the network is un-sync and the sync reasons are different
        VLAN, MTU and Bridge
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                },
                conf.MTU_STR: {
                    "expected": self.net_case_1_mtu_expected,
                    "actual": self.net_case_1_mtu_actual
                },
                conf.BRIDGE_STR: {
                    "expected": self.net_case_1_bridge_expected,
                    "actual": self.net_case_1_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons are "
            "different VLAN, MTU and Bridge"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_08.__name__)
class TestHostNetworkApiSync08(NetworkTest):
    """
    Check sync/un-sync for VLAN/MTU/Bridge on the same network over BOND
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[8][0]
    net_case_1_vlan_id_actual = None
    net_case_1_mtu_actual = str(net_conf.MTU[0])
    net_case_1_bridge_actual = "false"
    net_case_1_vlan_id_expected = conf.VLAN_IDS[55]
    net_case_1_mtu_expected = str(net_conf.MTU[1])
    net_case_1_bridge_expected = "true"
    bond_1 = "bond81"
    dummys = conf.DUMMYS[:2]

    @polarion("RHEVM3-13998")
    def test_unsync_network_change_vlan_mtu_bridge(self):
        """
        Check that the network is un-sync and the sync reasons are different
        VLAN, MTU and Bridge
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.VLAN_STR: {
                    "expected": self.net_case_1_vlan_id_expected,
                    "actual": self.net_case_1_vlan_id_actual
                },
                conf.MTU_STR: {
                    "expected": self.net_case_1_mtu_expected,
                    "actual": self.net_case_1_mtu_actual
                },
                conf.BRIDGE_STR: {
                    "expected": self.net_case_1_bridge_expected,
                    "actual": self.net_case_1_bridge_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons are "
            "different VLAN, MTU and Bridge"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_09.__name__)
class TestHostNetworkApiSync09(NetworkTest):
    """
    Check sync/un-sync for changed IP
    Sync the network
    """
    __test__ = True
    move_host = False
    ip_netmask = conf.IPS[37]
    net_case_1 = conf.SYNC_NETS_DC_1[9][0]
    net_case_1_ip_expected = ip_netmask
    net_case_1_ip_actual = "10.10.10.10"

    @polarion("RHEVM3-13999")
    def test_unsync_network_change_ip(self):
        """
        Check that the network is un-sync and the sync reasons is changed IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.IPADDR_STR: {
                    "expected": self.net_case_1_ip_expected,
                    "actual": self.net_case_1_ip_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is "
            "changed IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_10.__name__)
class TestHostNetworkApiSync10(NetworkTest):
    """
    Check sync/un-sync for changed netmask
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[10][0]
    net_case_1_netmask_expected = conf.IP_DICT_NETMASK["netmask"]
    net_case_1_netmask_actual = "255.255.255.255"
    ip_netmask = conf.IPS[37]

    @polarion("RHEVM3-14000")
    def test_unsync_network_change_netmask(self):
        """
        Check that the network is un-sync and the sync reason is changed
        netmask
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.NETMASK_STR: {
                    "expected": self.net_case_1_netmask_expected,
                    "actual": self.net_case_1_netmask_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "changed netmask"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_11.__name__)
class TestHostNetworkApiSync11(NetworkTest):
    """
    Check sync/un-sync for changed netmask prefix
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[11][0]
    net_case_1_netmask_prefix_expected = conf.IP_DICT_PREFIX["netmask"]
    net_case_1_netmask_prefix_actual = "255.255.255.255"
    ip_prefix = conf.IPS[41]

    @polarion("RHEVM3-14001")
    def test_unsync_network_change_netmask_prefix(self):
        """
        Check that the network is un-sync and the sync reasons is changed
        netmask prefix
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.NETMASK_STR: {
                    "expected": self.net_case_1_netmask_prefix_expected,
                    "actual": self.net_case_1_netmask_prefix_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is "
            "changed netmask prefix"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_12.__name__)
class TestHostNetworkApiSync12(NetworkTest):
    """
    Check sync/un-sync for changed IP over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    ip_netmask = conf.IPS[36]
    net_case_1 = conf.SYNC_NETS_DC_1[12][0]
    net_case_1_ip_expected = ip_netmask
    net_case_1_ip_actual = "10.10.10.10"
    bond_1 = "bond121"
    dummys = conf.DUMMYS[:2]

    @polarion("RHEVM3-14002")
    def test_unsync_network_change_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is changed IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.IPADDR_STR: {
                    "expected": self.net_case_1_ip_expected,
                    "actual": self.net_case_1_ip_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is "
            "changed IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_13.__name__)
class TestHostNetworkApiSync13(NetworkTest):
    """
    Check sync/un-sync for changed netmask over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[13][0]
    net_case_1_netmask_expected = conf.IP_DICT_NETMASK["netmask"]
    net_case_1_netmask_actual = "255.255.255.255"
    bond_1 = "bond131"
    ip_netmask = conf.IPS[35]
    dummys = conf.DUMMYS[:2]

    @polarion("RHEVM3-14003")
    def test_unsync_network_change_netmask_over_bond(self):
        """
        Check that the network is un-sync and the sync reason is changed
        netmask
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.NETMASK_STR: {
                    "expected": self.net_case_1_netmask_expected,
                    "actual": self.net_case_1_netmask_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reason is "
            "changed netmask"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_14.__name__)
class TestHostNetworkApiSync14(NetworkTest):
    """
    Check sync/un-sync for changed netmask prefix over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[14][0]
    net_case_1_netmask_prefix_expected = conf.IP_DICT_PREFIX["netmask"]
    net_case_1_netmask_prefix_actual = "255.255.255.255"
    bond_1 = "bond141"
    ip_prefix = conf.IPS[40]
    dummys = conf.DUMMYS[:2]

    @polarion("RHEVM3-14004")
    def test_unsync_network_change_netmask_prefix_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is changed
        netmask prefix
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.NETMASK_STR: {
                    "expected": self.net_case_1_netmask_prefix_expected,
                    "actual": self.net_case_1_netmask_prefix_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is "
            "changed netmask prefix"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_15.__name__)
class TestHostNetworkApiSync15(NetworkTest):
    """
    Check sync/un-sync for no-IP to IP
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[15][0]
    net_case_1_ip = "10.10.10.10"
    net_case_1_boot_proto_expected = "NONE"
    net_case_1_boot_proto_actual = "STATIC_IP"

    @polarion("RHEVM3-14009")
    def test_unsync_network_no_ip_to_ip(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BOOTPROTO_STR: {
                    "expected": self.net_case_1_boot_proto_expected,
                    "actual": self.net_case_1_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is new IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_16.__name__)
class TestHostNetworkApiSync16(NetworkTest):
    """
    Check sync/un-sync for no-IP to IP over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[16][0]
    net_case_1_ip = "10.10.10.10"
    net_case_1_boot_proto_expected = "NONE"
    net_case_1_boot_proto_actual = "STATIC_IP"
    bond_1 = "bond161"
    dummys = conf.DUMMYS[:2]

    @polarion("RHEVM3-14010")
    def test_unsync_network_no_ip_to_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BOOTPROTO_STR: {
                    "expected": self.net_case_1_boot_proto_expected,
                    "actual": self.net_case_1_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is new IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_17.__name__)
class TestHostNetworkApiSync17(NetworkTest):
    """
    Check sync/un-sync for removed IP
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[17][0]
    net_case_1_boot_proto_expected = "STATIC_IP"
    net_case_1_boot_proto_actual = "NONE"
    ip_netmask = conf.IPS[34]

    @polarion("RHEVM3-14011")
    def test_unsync_network_remove_ip(self):
        """
        Check that the network is un-sync and the sync reasons is no IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BOOTPROTO_STR: {
                    "expected": self.net_case_1_boot_proto_expected,
                    "actual": self.net_case_1_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is no IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_18.__name__)
class TestHostNetworkApiSync18(NetworkTest):
    """
    Check sync/un-sync for removed IP over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[18][0]
    net_case_1_boot_proto_expected = "STATIC_IP"
    net_case_1_boot_proto_actual = "NONE"
    ip_netmask = conf.IPS[33]

    @polarion("RHEVM3-14012")
    def test_unsync_network_remove_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is no IP
        Sync the network
        """
        compare_dict = {
            self.net_case_1: {
                conf.BOOTPROTO_STR: {
                    "expected": self.net_case_1_boot_proto_expected,
                    "actual": self.net_case_1_boot_proto_actual
                }
            }
        }
        testflow.step(
            "Check that the network is un-sync and the sync reasons is no IP"
        )
        self.assertTrue(
            helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        )
        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_19.__name__)
class TestHostNetworkApiSync19(NetworkTest):
    """
    Check sync/un-sync for:
     1. Changed QoS
     2. No QoS to QoS
     3. QoS to no QoS
    Sync the network
    """
    __test__ = True
    move_host = True
    net_case_1 = conf.SYNC_NETS_DC_1[19][0]
    net_case_1_qos_expected = "20"
    net_case_1_qos_actual = "10"
    net_case_2 = conf.SYNC_NETS_DC_1[19][1]
    net_case_2_qos_expected = "10"
    net_case_2_qos_actual = None
    net_case_3 = conf.SYNC_NETS_DC_1[19][2]
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

    @polarion("RHEVM3-14026")
    def test_unsync_network_change_qos(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons changed "
            "QoS"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-14027")
    def test_unsync_network_no_qos_to_qos(self):
        """
        Check that the network is un-sync and the sync reasons no QoS
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons no QoS"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-14028")
    def test_unsync_network_qos_to_no_qos(self):
        """
        Check that the network is un-sync and the sync reasons QoS
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons QoS"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )


@tier2
@attr(tier=2)
@pytest.mark.usefixtures(sync_case_20.__name__)
class TestHostNetworkApiSync20(NetworkTest):
    """
    Check sync/un-sync over BOND for:
     1. Changed QoS
     2. No QoS to QoS
     3. QoS to no QoS
    Sync the network
    """
    __test__ = True
    move_host = True
    bond_1 = "bond201"
    bond_2 = "bond202"
    bond_3 = "bond203"
    dummys_1 = conf.DUMMYS[:2]
    dummys_2 = conf.DUMMYS[2:4]
    dummys_3 = conf.DUMMYS[4:6]
    net_case_1 = conf.SYNC_NETS_DC_1[20][0]
    net_case_1_qos_expected = "20"
    net_case_1_qos_actual = "10"
    net_case_2 = conf.SYNC_NETS_DC_1[20][1]
    net_case_2_qos_expected = "10"
    net_case_2_qos_actual = None
    net_case_3 = conf.SYNC_NETS_DC_1[20][2]
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

    @polarion("RHEVM3-14029")
    def test_unsync_network_change_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        over BOND
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons changed "
            "QoS over BOND"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_1]
            )
        )

    @polarion("RHEVM3-14030")
    def test_unsync_network_no_qos_to_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons no QoS over BOND
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons no QoS "
            "over BOND"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_2]
            )
        )

    @polarion("RHEVM3-14031")
    def test_unsync_network_qos_to_no_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons QoS over BOND
        Sync the network
        """
        testflow.step(
            "Check that the network is un-sync and the sync reasons QoS over "
            "BOND"
        )
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }
            self.assertTrue(
                helper.get_networks_sync_status_and_unsync_reason(
                    compare_dict_
                )
            )

        testflow.step("Sync the network")
        self.assertTrue(
            network_helper.sync_networks(
                host=net_conf.HOST_0_NAME, networks=[self.net_case_3]
            )
        )
