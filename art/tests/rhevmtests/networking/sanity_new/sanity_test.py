#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import logging
import config as conf
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.arbitrary_vlan_device_name.helper as vlan_helper


logger = logging.getLogger("Sanity_Cases")


@attr(tier=1)
class TestSanityCaseBase(NetworkTest):
    """
    Base class which provides teardown class method for each test case
    that inherits this class
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the host NICs.
        """
        logger.info("Removing all networks from %s", conf.HOST_NAME_0)
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error(
                "Failed to remove all networks from %s", conf.HOST_NAME_0
            )


class TestSanity01(TestSanityCaseBase):
    """
    1. Create VLAN entity with name on the host
    2. Check that the VLAN network exists on host via engine
    3. Attach the vlan to bridge
    4. Add the bridge with VLAN to virsh
    5. Remove the VLAN/bridge and clean host interfaces
    """

    __test__ = True
    apis = set(["rest"])
    vlan_id = conf.VLAN_IDS[0]
    vlan_name = vlan_helper.VLAN_NAMES[0]
    bridge_name = vlan_helper.BRIDGE_NAMES[0]

    @classmethod
    def setup_class(cls):
        """
        Create VLAN entity with name on the host
        """
        vlan_helper.add_vlans_to_host(
            host_obj=conf.VDS_HOST_0, nic=1, vlan_id=[cls.vlan_id],
            vlan_name=[cls.vlan_name]
        )
        vlan_helper.add_bridge_on_host_and_virsh(
            host_obj=conf.VDS_HOST_0, bridge=[cls.bridge_name],
            network=[cls.vlan_name]
        )

    @polarion("RHEVM3-4170")
    def test_vlan_on_nic(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        vlan_helper.check_if_nic_in_host_nics(
            nic=self.vlan_name, host=conf.HOST_NAME_0
        )
        vlan_helper.check_if_nic_in_vdscaps(
            host_obj=conf.VDS_HOST_0, nic=self.bridge_name
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN/bridge and clean host interfaces
        """
        vlan_helper.job_tear_down()


class TestSanity02(TestSanityCaseBase):
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
    net = conf.NETS[2]
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    bond_4 = "bond24"
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
                nic=conf.HOST_0_NICS[2], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[0]
                },
                "2": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[1],
                },
                "3": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX,
                    "properties": properties_dict
                },
                "4": {
                    "nic": self.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "5": {
                    "nic": self.bond_1,
                    "network": self.net[3],
                    "ip": conf.BASIC_IP_DICT_NETMASK
                },
                "6": {
                    "nic": self.bond_1,
                    "network": self.net[4],
                },
                "7": {
                    "nic": self.bond_2,
                    "slaves": conf.DUMMYS[2:4]
                },
                "8": {
                    "nic": self.bond_3,
                    "slaves": conf.DUMMYS[6:9]
                },
                "9": {
                    "nic": self.bond_4,
                    "slaves": conf.DUMMYS[9:11]
                }

            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_NAME_0)
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_NAME_0
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
                    "nic": self.bond_1,
                    "network": self.net[1],
                },
                "2": {
                    "nic": conf.DUMMYS[11],
                    "network": self.net[2],
                    "ip": conf.BASIC_IP_DICT_PREFIX
                },
                "3": {
                    "nic": self.bond_2,
                    "network": self.net[4],
                },
                "4": {
                    "nic": self.bond_2,
                    "slaves": conf.DUMMYS[2:5]
                },
                "5": {
                    "nic": self.bond_3,
                    "slaves": conf.DUMMYS[6:8]
                },
            },
            "remove": {
                "networks": [
                    self.net[0],
                    self.net[3]
                ],
                "bonds": [self.bond_4]
            },
            "add": {
                "1": {
                    "nic": self.bond_3,
                    "network": self.net[5]
                }
            }
        }
        logger.info(
            "Perform SetupNetwork update action on %s", conf.HOST_NAME_0
        )
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Update SetupNetwork action failed on %s" % conf.HOST_NAME_0
            )


class TestSanity03(TestSanityCaseBase):
    """
    Add new network QOS (named)
    """

    __test__ = True
    qos_name = conf.QOS_NAME[0]
    qos_value = conf.QOS_TEST_VALUE
    bz = {"1274187": {"engine": None, "version": ["3.6"]}}

    @polarion("RHEVM3-6525")
    def test_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Fill in weighted share only for this QoS
        3) Fill in all 3 values for this QoS:
        a) weighted share, b) rate limit, c) committed rate
        4) Update the provided values
        """
        network_helper.create_host_net_qos(
            qos_name=self.qos_name, outbound_average_linkshare=self.qos_value
        )

        logger.info(
            "Update existing Host Network QoS profile under DC by adding rate "
            "limit and committed rate"
        )
        network_helper.update_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_upperlimit=self.qos_value,
            outbound_average_realtime=self.qos_value
        )
        logger.info(
            "Update weighted share, limit and committed rate for existing QoS"
        )
        network_helper.update_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=self.qos_value + 1,
            outbound_average_upperlimit=self.qos_value + 1,
            outbound_average_realtime=self.qos_value + 1
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        network_helper.remove_qos_from_dc(qos_name=cls.qos_name)


class TestSanity04(TestSanityCaseBase):
    """
    Test MTU over VM/Non-VM/VLAN and BOND
    """

    __test__ = True
    net = conf.NETS[4]
    bond = "bond21"

    def test_mtu_over_vm(self):
        """
        Create network with MTU 5000 over VM network
        """
        mtu_over_vm_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[0]
                }
            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_NAME_0)
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **mtu_over_vm_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_NAME_0
            )

    def test_mtu_over_non_vm(self):
        """
        Create network with MTU 5000 over Non-VM network
        """
        mtu_over_non_vm_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[2],
                    "network": self.net[1]
                }
            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_NAME_0)
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **mtu_over_non_vm_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_NAME_0
            )

    def test_mtu_over_vlan(self):
        """
        Create network with MTU 5000 over VLAN network
        """
        mtu_over_vlan_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[2],
                    "network": self.net[2]
                }
            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_NAME_0)
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **mtu_over_vlan_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_NAME_0
            )

    @polarion("RHEVM3-XXX")
    def test_mtu_over_bond(self):
        """
        Create network with MTU 5000 over BOND
        """
        mtu_over_bond_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": self.bond,
                    "network": self.net[3]
                }
            }
        }
        logger.info("Perform SetupNetwork action on %s",  conf.HOST_NAME_0)
        if not hl_host_network.setup_networks(
            conf.HOST_NAME_0, **mtu_over_bond_dict
        ):
            raise conf.NET_EXCEPTION(
                "SetupNetwork action failed on %s" % conf.HOST_NAME_0
            )
