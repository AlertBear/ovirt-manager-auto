#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sync tests from host network API
"""

import helper
import logging
import config as conf
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Sync_Cases")


def setup_module():
    """
    Creates datacenter, clusters, and add networks
    """
    logger.info("Creating %s and %s", conf.EXTRA_DC, conf.EXTRA_CL)
    if not hl_networks.create_basic_setup(
        datacenter=conf.EXTRA_DC, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION, cluster=conf.EXTRA_CL, cpu=conf.CPU_NAME
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create extra setup%s and %s" %
            (conf.EXTRA_DC, conf.EXTRA_CL)
        )
    logger.info(
        "Add %s to %s/%s", conf.SYNC_DICT_1, conf.DC_NAME, conf.CLUSTER_2
    )
    helper.prepare_networks_on_dc(
        networks_dict=conf.SYNC_DICT_1, cluster=conf.CLUSTER_2
    )
    logger.info(
        "Add %s to %s/%s", conf.SYNC_DICT_2, conf.EXTRA_DC, conf.EXTRA_CL
    )
    helper.prepare_networks_on_dc(
        networks_dict=conf.SYNC_DICT_2, dc=conf.EXTRA_DC, cluster=conf.EXTRA_CL
    )


def teardown_module():
    """
    Removes created datacenter, cluster and networks
    """
    logger.info("Removing extra %s and %s", conf.EXTRA_DC, conf.EXTRA_CL)
    if not hl_networks.remove_basic_setup(
        datacenter=conf.EXTRA_DC, cluster=conf.EXTRA_CL
    ):
        logger.error(
            "Failed to remove %s and %s", conf.EXTRA_DC, conf.EXTRA_CL
        )
    if not hl_networks.remove_net_from_setup(
        host=conf.VDS_HOSTS_1, auto_nics=[0], all_net=True,
        mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove %s from setup", conf.SYNC_DICT_1.keys()
        )


class TestHostNetworkApiSyncBase(helper.TestHostNetworkApiTestCaseBase):
    """
    Base class for sync test
    """
    __test__ = False
    network_host_api_dict = None

    @classmethod
    def setup_class(cls):
        """
        Attach networks to the host
        Move the host the another cluster
        """
        logger.info(
            "Attaching networks to %s on %s", conf.HOST_4_NICS[1], conf.HOST_4)
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_4, **cls.network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach networks to %s on %s" % (
                    conf.HOST_4_NICS[1], conf.HOST_4
                )
            )
        if not net_help.move_host_to_another_cluster(
            conf.HOST_4, conf.EXTRA_CL
        ):
            raise conf.NET_EXCEPTION(
                "Failed to move %s to %s", conf.HOST_4, conf.EXTRA_CL
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
        if not net_help.move_host_to_another_cluster(
            conf.HOST_4, conf.CLUSTER_2
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
    net_case_2 = conf.SYNC_NETS_DC_1[1][1]
    net_case_2_vlan_id_actual = conf.VLAN_IDS[37]
    net_case_3 = conf.SYNC_NETS_DC_1[1][2]
    net_case_3_vlan_id_actual = None
    net_case_1_vlan_id_expected = conf.VLAN_IDS[40]
    net_case_2_vlan_id_expected = None
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
                    "nic": conf.HOST_1_NICS[1],
                    "datacenter": conf.DC_NAME
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_1_NICS[2],
                    "datacenter": conf.DC_NAME
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_1_NICS[3],
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
    net_case_2 = conf.SYNC_NETS_DC_1[2][1]
    net_case_2_vlan_id_actual = conf.VLAN_IDS[43]
    net_case_3 = conf.SYNC_NETS_DC_1[2][2]
    net_case_3_vlan_id_actual = None
    net_case_1_vlan_id_expected = conf.VLAN_IDS[44]
    net_case_2_vlan_id_expected = None
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
    net_case_2 = conf.SYNC_NETS_DC_1[3][1]
    net_case_2_mtu_actual = str(conf.MTU[1])
    net_case_3 = conf.SYNC_NETS_DC_1[3][2]
    net_case_3_mtu_actual = str(conf.MTU[3])
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_2_mtu_expected = str(conf.MTU[3])
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
                    "nic": conf.HOST_1_NICS[1],
                    "datacenter": conf.DC_NAME
                },
                "2": {
                    "network": cls.net_case_2,
                    "nic": conf.HOST_1_NICS[2],
                    "datacenter": conf.DC_NAME
                },
                "3": {
                    "network": cls.net_case_3,
                    "nic": conf.HOST_1_NICS[3],
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
    net_case_2 = conf.SYNC_NETS_DC_1[4][1]
    net_case_2_mtu_actual = str(conf.MTU[1])
    net_case_3 = conf.SYNC_NETS_DC_1[4][2]
    net_case_3_mtu_actual = str(conf.MTU[3])
    net_case_1_mtu_expected = str(conf.MTU[1])
    net_case_2_mtu_expected = str(conf.MTU[3])
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
