#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import helper
import logging
import config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Sync_Cases")


def setup_module():
    """
    Creates datacenter, cluster, and add networks
    """
    logger.info("Creating %s and %s", conf.SYNC_DC, conf.SYNC_CL)
    if not hl_networks.create_basic_setup(
        datacenter=conf.SYNC_DC, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION, cluster=conf.SYNC_CL, cpu=conf.CPU_NAME
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create extra setup %s and %s" %
            (conf.SYNC_DC, conf.SYNC_CL)
        )
    logger.info(
        "Add %s to %s/%s", conf.SYNC_DICT_1, conf.DC_NAME_1,
        conf.CLUSTER_NAME_1
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.SYNC_DICT_1, dc=conf.DC_NAME_1,
        cluster=conf.CLUSTER_NAME_1
    )
    logger.info(
        "Add %s to %s/%s", conf.SYNC_DICT_2, conf.SYNC_DC, conf.SYNC_CL
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.SYNC_DICT_2, dc=conf.SYNC_DC, cluster=conf.SYNC_CL
    )
    logger.info("Deactivate %s", conf.HOST_0_NAME)
    if not ll_hosts.deactivateHost(True, conf.HOST_0_NAME):
        raise conf.NET_EXCEPTION(
            "Failed to set %s to maintenance" % conf.HOST_0_NAME
        )


def teardown_module():
    """
    Removes created datacenter, cluster and networks
    """
    logger.info("Removing extra %s and %s", conf.SYNC_DC, conf.SYNC_CL)
    if not hl_networks.remove_basic_setup(
        datacenter=conf.SYNC_DC, cluster=conf.SYNC_CL
    ):
        logger.error(
            "Failed to remove %s and %s", conf.SYNC_DC, conf.SYNC_CL
        )
    if not hl_networks.remove_net_from_setup(
        host=conf.HOST_0_NAME, all_net=True, mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove %s from setup", conf.SYNC_DICT_1.keys()
        )
    logger.info("Activate %s", conf.HOST_0_NAME)
    if not ll_hosts.activateHost(positive=True, host=conf.HOST_0_NAME):
        logger.error("Failed to activate %s", conf.HOST_0_NAME)


class TestHostNetworkApiSyncBase(helper.TestHostNetworkApiTestCaseBase):
    """
    Base class for sync test
    """
    __test__ = False
    network_host_api_dict = None
    move_host = True

    @classmethod
    def setup_class(cls):
        """
        Attach networks to the host
        Move the host the another cluster
        """
        logger.info("Attaching networks to %s", conf.HOST_0_NAME)
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **cls.network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach networks to %s" % conf.HOST_0_NAME
            )
        if cls.move_host:
            if not ll_hosts.updateHost(
                positive=True, host=conf.HOST_0_NAME, cluster=conf.SYNC_CL
            ):
                raise conf.NET_EXCEPTION(
                    "Failed to move %s to %s" %
                    (conf.HOST_0_NAME, conf.SYNC_CL)
                )

    @classmethod
    def teardown_class(cls):
        """
        Clean the host interface
        Move the host back to the original cluster
        """
        logger.info("Removing all networks from %s", conf.HOST_0_NAME)
        if not hl_host_network.clean_host_interfaces(conf.HOST_0_NAME):
            logger.error(
                "Failed to remove all networks from %s", conf.HOST_0_NAME
            )
        if cls.move_host:
            if not ll_hosts.updateHost(
                positive=True, host=conf.HOST_0_NAME,
                cluster=conf.CLUSTER_NAME_1
            ):
                logger.error(
                    "Failed to move %s to %s",
                    conf.HOST_0_NAME, conf.CLUSTER_NAME_1
                )


class TestHostNetworkApiSync01(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync different VLAN networks
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[1][0]
    net_case_1_vlan_id_actual = conf.VLAN_IDS[36]
    net_case_1_vlan_id_expected = conf.VLAN_IDS[40]
    net_case_2 = conf.SYNC_NETS_DC_1[1][1]
    net_case_2_vlan_id_actual = conf.VLAN_IDS[37]
    net_case_2_vlan_id_expected = None
    net_case_3 = conf.SYNC_NETS_DC_1[1][2]
    net_case_3_vlan_id_actual = None
    net_case_3_vlan_id_expected = conf.VLAN_IDS[41]

    @classmethod
    def setup_class(cls):
        """
        Attach networks with VLAN/Non-VLAN to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync01.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "datacenter": conf.DC_NAME_1
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_0_NICS[2],
                    "datacenter": conf.DC_NAME_1
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_0_NICS[3],
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync01, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )


class TestHostNetworkApiSync02(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync different VLAN networks over BOND
    Sync the network
    """
    __test__ = True
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

    @classmethod
    def setup_class(cls):
        """
        Attach networks with VLAN/Non-VLAN to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync02.network_host_api_dict = {
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
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "datacenter": conf.DC_NAME_1
                },
                "5": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME_1
                },
                "6": {
                    "network": cls.net_case_3,
                    "nic": cls.bond_3,
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync02, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )


class TestHostNetworkApiSync03(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync different MTU networks over NIC
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[3][0]
    net_case_1_mtu_actual = str(conf.MTU[0])
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_2 = conf.SYNC_NETS_DC_1[3][1]
    net_case_2_mtu_actual = str(conf.MTU[1])
    net_case_2_mtu_expected = str(conf.MTU[3])
    net_case_3 = conf.SYNC_NETS_DC_1[3][2]
    net_case_3_mtu_actual = str(conf.MTU[3])
    net_case_3_mtu_expected = str(conf.MTU[0])

    @classmethod
    def setup_class(cls):
        """
        Attach networks with MTU/Non-MTU to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync03.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "datacenter": conf.DC_NAME_1
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_0_NICS[2],
                    "datacenter": conf.DC_NAME_1
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_0_NICS[3],
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync03, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )


class TestHostNetworkApiSync04(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync different MTU networks over BOND
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[4][0]
    net_case_1_mtu_actual = str(conf.MTU[0])
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_2 = conf.SYNC_NETS_DC_1[4][1]
    net_case_2_mtu_actual = str(conf.MTU[1])
    net_case_2_mtu_expected = str(conf.MTU[3])
    net_case_3 = conf.SYNC_NETS_DC_1[4][2]
    net_case_3_mtu_actual = str(conf.MTU[3])
    net_case_3_mtu_expected = str(conf.MTU[0])
    bond_1 = "bond31"
    bond_2 = "bond32"
    bond_3 = "bond33"

    @classmethod
    def setup_class(cls):
        """
        Attach networks with MTU/Non-MTU to the host over BOND
        Move the host to another cluster
        """
        TestHostNetworkApiSync04.network_host_api_dict = {
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
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "datacenter": conf.DC_NAME_1
                },
                "5": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME_1
                },
                "6": {
                    "network": cls.net_case_3,
                    "nic": cls.bond_3,
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync04, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )


class TestHostNetworkApiSync05(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for VM/Non-VM networks over NIC
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[5][0]
    net_case_1_bridge_actual = "true"
    net_case_1_bridge_expected = "false"
    net_case_2 = conf.SYNC_NETS_DC_1[5][1]
    net_case_2_bridge_actual = "false"
    net_case_2_bridge_expected = "true"

    @classmethod
    def setup_class(cls):
        """
        Attach networks with VM/Non-VM to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync05.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "datacenter": conf.DC_NAME_1
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_0_NICS[2],
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync05, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )


class TestHostNetworkApiSync06(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for VM/Non-VM networks over BOND
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[6][0]
    net_case_1_bridge_actual = "true"
    net_case_1_bridge_expected = "false"
    net_case_2 = conf.SYNC_NETS_DC_1[6][1]
    net_case_2_bridge_actual = "false"
    net_case_2_bridge_expected = "true"
    bond_1 = "bond61"
    bond_2 = "bond62"

    @classmethod
    def setup_class(cls):
        """
        Attach networks with VM/Non-VM to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync06.network_host_api_dict = {
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
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "datacenter": conf.DC_NAME_1
                },
                "4": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync06, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )


class TestHostNetworkApiSync07(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for VLAN/MTU/Bridge on the same network
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[7][0]
    net_case_1_vlan_id_actual = None
    net_case_1_mtu_actual = str(conf.MTU[0])
    net_case_1_bridge_actual = "false"
    net_case_1_vlan_id_expected = conf.VLAN_IDS[54]
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_1_bridge_expected = "true"

    @classmethod
    def setup_class(cls):
        """
        Attach network with non-VLAN, non-VM with default MTU to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync07.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync07, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync08(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for VLAN/MTU/Bridge on the same network over BOND
    Sync the network
    """
    __test__ = True
    net_case_1 = conf.SYNC_NETS_DC_1[8][0]
    net_case_1_vlan_id_actual = None
    net_case_1_mtu_actual = str(conf.MTU[0])
    net_case_1_bridge_actual = "false"
    net_case_1_vlan_id_expected = conf.VLAN_IDS[55]
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_1_bridge_expected = "true"
    bond_1 = "bond81"

    @classmethod
    def setup_class(cls):
        """
        Attach networks with  non-VLAN, non-VM with default MTU to the host
        Move the host to another cluster
        """
        TestHostNetworkApiSync08.network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync08, cls).setup_class()

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync09(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the IP on attached network
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync09.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync09, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip_actual, interface=cls.net_case_1
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync10(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the netmask on attached network
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync10.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync10, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, netmask=cls.net_case_1_netmask_actual
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync11(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the netmask prefix on the attached network
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = cls.ip_prefix
        TestHostNetworkApiSync11.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_PREFIX,
                }
            }
        }
        super(TestHostNetworkApiSync11, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1,
            netmask=cls.net_case_1_netmask_prefix_actual
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync12(TestHostNetworkApiSyncBase):
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

    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the IP on attached network
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync12.network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync12, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip_actual, interface=cls.net_case_1
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync13(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the netmask on attached network
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync13.network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync13, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, netmask=cls.net_case_1_netmask_actual
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync14(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the netmask prefix on the attached network
        """
        conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = cls.ip_prefix
        TestHostNetworkApiSync14.network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "ip": conf.BASIC_IP_DICT_PREFIX,
                }
            }
        }
        super(TestHostNetworkApiSync14, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1,
            netmask=cls.net_case_1_netmask_prefix_actual
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync15(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for no-IP to IP
    Sync the network
    """
    __test__ = True
    bz = {"1270807": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[15][0]
    net_case_1_ip = "10.10.10.10"
    net_case_1_boot_proto_expected = "NONE"
    net_case_1_boot_proto_actual = "STATIC_IP"

    @classmethod
    def setup_class(cls):
        """
        Attach network without IP to the host
        Add the IP to the attached network
        """
        TestHostNetworkApiSync15.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                }
            }
        }
        super(TestHostNetworkApiSync15, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip, interface=cls.net_case_1
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync16(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for no-IP to IP over BOND
    Sync the network
    """
    __test__ = True
    bz = {"1270807": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[16][0]
    net_case_1_ip = "10.10.10.10"
    net_case_1_boot_proto_expected = "NONE"
    net_case_1_boot_proto_actual = "STATIC_IP"
    bond_1 = "bond161"

    @classmethod
    def setup_class(cls):
        """
        Attach network without IP to the host over BOND
        Add the IP on attached network
        """
        TestHostNetworkApiSync16.network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,

                }
            }
        }
        super(TestHostNetworkApiSync16, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip, interface=cls.net_case_1
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync17(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host
        Remove the IP from the host
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync17.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync17, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, set_ip=False
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync18(TestHostNetworkApiSyncBase):
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
    bz = {"1298534": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host over BOND
        Remove the IP from the host
        """
        conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = cls.ip_netmask
        TestHostNetworkApiSync18.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync18, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, set_ip=False
        )

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
        helper.get_networks_sync_status_and_unsync_reason(compare_dict)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )


class TestHostNetworkApiSync19(TestHostNetworkApiSyncBase):
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

    @classmethod
    def setup_class(cls):
        """
        Attach networks to the host
        """
        TestHostNetworkApiSync19.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_0_NICS[1],
                    "datacenter": conf.DC_NAME_1
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_0_NICS[2],
                    "datacenter": conf.DC_NAME_1
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_0_NICS[3],
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync19, cls).setup_class()

    @polarion("RHEVM3-14026")
    def test_unsync_network_change_qos(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-14027")
    def test_unsync_network_no_qos_to_qos(self):
        """
        Check that the network is un-sync and the sync reasons no QoS
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-14028")
    def test_unsync_network_qos_to_no_qos(self):
        """
        Check that the network is un-sync and the sync reasons QoS
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )


class TestHostNetworkApiSync20(TestHostNetworkApiSyncBase):
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

    @classmethod
    def setup_class(cls):
        """
        Attach networks to the host over BOND
        """
        TestHostNetworkApiSync20.network_host_api_dict = {
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
                    "slaves": conf.DUMMYS[4:6],
                },
                "4": {
                    "network": cls.net_case_1,
                    "nic": cls.bond_1,
                    "datacenter": conf.DC_NAME_1
                },
                "5": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME_1
                },
                "6": {
                    "network": cls.net_case_3,
                    "nic": cls.bond_3,
                    "datacenter": conf.DC_NAME_1
                }
            }
        }
        super(TestHostNetworkApiSync20, cls).setup_class()

    @polarion("RHEVM3-14029")
    def test_unsync_network_change_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons changed QoS
        over BOND
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_1: {
                    qos_value: self.expected_actual_dict_1
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_1]
        )

    @polarion("RHEVM3-14030")
    def test_unsync_network_no_qos_to_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons no QoS over BOND
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_2: {
                    qos_value: self.expected_actual_dict_2
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_2]
        )

    @polarion("RHEVM3-14031")
    def test_unsync_network_qos_to_no_qos_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons QoS over BOND
        Sync the network
        """
        for qos_value in conf.QOS_VALUES:
            compare_dict_ = {
                self.net_case_3: {
                    qos_value: self.expected_actual_dict_3
                }
            }

            helper.get_networks_sync_status_and_unsync_reason(compare_dict_)
        network_helper.sync_networks(
            host=conf.HOST_0_NAME, networks=[self.net_case_3]
        )
