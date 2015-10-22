#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import helper
import logging
import config as conf
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.helper as net_helper

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
        "Add %s to %s/%s", conf.SYNC_DICT_1, conf.DC_NAME, conf.CLUSTER_2
    )
    net_helper.prepare_networks_on_setup(
        networks_dict=conf.SYNC_DICT_1, dc=conf.DC_NAME, cluster=conf.CLUSTER_2
    )
    logger.info(
        "Add %s to %s/%s", conf.SYNC_DICT_2, conf.SYNC_DC, conf.SYNC_CL
    )
    net_helper.prepare_networks_on_setup(
        networks_dict=conf.SYNC_DICT_2, dc=conf.SYNC_DC, cluster=conf.SYNC_CL
    )
    logger.info("Deactivate %s", conf.HOST_4)
    if not ll_hosts.deactivateHost(True, conf.HOST_4):
        raise conf.NET_EXCEPTION(
            "Failed to set %s to maintenance" % conf.HOST_4
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
        host=conf.VDS_HOSTS_4, auto_nics=[0], all_net=True,
        mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove %s from setup", conf.SYNC_DICT_1.keys()
        )
    logger.info("Activate %s", conf.HOST_4)
    if not ll_hosts.activateHost(positive=True, host=conf.HOST_4):
        logger.error("Failed to activate %s", conf.HOST_4)


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
        logger.info("Attaching networks to %s", conf.HOST_4)
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **cls.network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach networks to %s" % conf.HOST_4
            )
        if cls.move_host:
            if not ll_hosts.updateHost(
                positive=True, host=conf.HOST_4, cluster=conf.SYNC_CL
            ):
                raise conf.NET_EXCEPTION(
                    "Failed to move %s to %s" % (conf.HOST_4, conf.SYNC_CL)
                )

    @classmethod
    def teardown_class(cls):
        """
        Clean the host interface
        Move the host back to the original cluster
        """
        logger.info("Removing all networks from %s", conf.HOST_4)
        if not hl_host_network.clean_host_interfaces(conf.HOST_4):
            logger.error(
                "Failed to remove all networks from %s", conf.HOST_4
            )
        if not ll_hosts.updateHost(
            positive=True, host=conf.HOST_4, cluster=conf.CLUSTER_2
        ):
            logger.error(
                "Failed to move %s to %s", conf.HOST_4, conf.CLUSTER_2
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
                    "nic": conf.HOST_4_NICS[1],
                    "datacenter": conf.DC_NAME
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_4_NICS[2],
                    "datacenter": conf.DC_NAME
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_4_NICS[3],
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync01, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])

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
        helper.sync_networks([self.net_case_3])


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
                    "datacenter": conf.DC_NAME
                },
                "5": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME
                },
                "6": {
                    "network": cls.net_case_3,
                    "nic": cls.bond_3,
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync02, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])

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
        helper.sync_networks([self.net_case_3])


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
                    "nic": conf.HOST_4_NICS[1],
                    "datacenter": conf.DC_NAME
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_4_NICS[2],
                    "datacenter": conf.DC_NAME
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_4_NICS[3],
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync03, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])

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
        helper.sync_networks([self.net_case_3])


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
                    "datacenter": conf.DC_NAME
                },
                "5": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME
                },
                "6": {
                    "network": cls.net_case_3,
                    "nic": cls.bond_3,
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync04, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])

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
        helper.sync_networks([self.net_case_3])


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
                    "nic": conf.HOST_4_NICS[1],
                    "datacenter": conf.DC_NAME
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_4_NICS[2],
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync05, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])


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
                    "datacenter": conf.DC_NAME
                },
                "4": {
                    "network": cls.net_case_2,
                    "nic": cls.bond_2,
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync06, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])

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
        helper.sync_networks([self.net_case_2])


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
                    "nic": conf.HOST_4_NICS[1],
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync07, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])


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
                    "datacenter": conf.DC_NAME
                }
            }
        }
        super(TestHostNetworkApiSync08, cls).setup_class()

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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync09(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for changed IP
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[9][0]
    net_case_1_ip_expected = conf.IP_DICT_NETMASK["address"]
    net_case_1_ip_actual = "10.10.10.10"

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the IP on attached network
        """
        TestHostNetworkApiSync09.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync09, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip_actual, interface=cls.net_case_1
        )

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
        helper.sync_networks([self.net_case_1])


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

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the netmask on attached network
        """
        TestHostNetworkApiSync10.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync10, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, netmask=cls.net_case_1_netmask_actual
        )

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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync11(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for changed netmask prefix
    Sync the network
    """
    __test__ = True
    bz = {"1269481": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[11][0]
    net_case_1_netmask_prefix_expected = conf.IP_DICT_PREFIX["netmask"]
    net_case_1_netmask_prefix_actual = "32"

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host
        Change the netmask prefix on the attached network
        """
        TestHostNetworkApiSync11.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_PREFIX,
                }
            }
        }
        super(TestHostNetworkApiSync11, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1,
            netmask=cls.net_case_1_netmask_prefix_actual
        )

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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync12(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for changed IP over BOND
    Sync the network
    """
    __test__ = True
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[12][0]
    net_case_1_ip_expected = conf.IP_DICT_NETMASK["address"]
    net_case_1_ip_actual = "10.10.10.10"
    bond_1 = "bond121"

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the IP on attached network
        """
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
        helper.sync_networks([self.net_case_1])


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

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the netmask on attached network
        """
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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync14(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for changed netmask prefix over BOND
    Sync the network
    """
    __test__ = True
    bz = {"1269481": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[14][0]
    net_case_1_netmask_prefix_expected = conf.IP_DICT_PREFIX["netmask"]
    net_case_1_netmask_prefix_actual = "32"
    bond_1 = "bond141"

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host over BOND
        Change the netmask prefix on the attached network
        """
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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync15(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for no-IP to IP
    Sync the network
    """
    __test__ = True
    bz = {"1270807": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[15][0]
    net_case_1_ip_expected = None
    net_case_1_ip_actual = "10.10.10.10"

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
                    "nic": conf.HOST_4_NICS[1],
                }
            }
        }
        super(TestHostNetworkApiSync15, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            ip=cls.net_case_1_ip_actual, interface=cls.net_case_1
        )

    def test_unsync_network_no_ip_to_ip(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
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
        helper.sync_networks([self.net_case_1])


class TestHostNetworkApiSync16(TestHostNetworkApiSyncBase):
    """
    Check sync/un-sync for no-IP to IP over BOND
    Sync the network
    """
    __test__ = True
    bz = {"1270807": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    move_host = False
    net_case_1 = conf.SYNC_NETS_DC_1[16][0]
    net_case_1_ip_expected = None
    net_case_1_ip_actual = "10.10.10.10"
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
            ip=cls.net_case_1_ip_actual, interface=cls.net_case_1
        )

    def test_unsync_network_no_ip_to_ip_over_bond(self):
        """
        Check that the network is un-sync and the sync reasons is new IP
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
        helper.sync_networks([self.net_case_1])


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

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP to the host
        Remove the IP from the host
        """
        TestHostNetworkApiSync17.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync17, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, set_ip=False
        )

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
        helper.sync_networks([self.net_case_1])


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

    @classmethod
    def setup_class(cls):
        """
        Attach network with IP the host over BOND
        Remove the IP from the host
        """
        TestHostNetworkApiSync18.network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_case_1,
                    "nic": conf.HOST_4_NICS[1],
                    "ip": conf.BASIC_IP_DICT_NETMASK,
                }
            }
        }
        super(TestHostNetworkApiSync18, cls).setup_class()
        helper.manage_ip_and_refresh_capabilities(
            interface=cls.net_case_1, set_ip=False
        )

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
        helper.sync_networks([self.net_case_1])
