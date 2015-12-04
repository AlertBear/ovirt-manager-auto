#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.arbitrary_vlan_device_name.helper as vlan_helper


logger = logging.getLogger("Sanity_Cases")


@unittest_lib.attr(tier=1)
class TestSanityCaseBase(unittest_lib.NetworkTest):
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
        helper.send_setup_networks(sn_dict=network_host_api_dict)

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
        helper.send_setup_networks(sn_dict=network_host_api_dict)


class TestSanity03(TestSanityCaseBase):
    """
    Add new network QOS (named)
    Attach network with QoS to host NIC
    """
    __test__ = True
    qos_name = conf.QOS_NAME[3]
    net = conf.NETS[3][0]

    @polarion("RHEVM3-6525")
    @bz({"1274187": {"engine": None, "version": ["3.6"]}})
    def test_add_network_qos(self):
        """
        Create new Host Network QoS profile under DC
        """
        network_helper.create_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.TEST_VALUE
        )

    @polarion("RHEVM3-6526")
    def test_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_realtime": conf.TEST_VALUE,
                        "outbound_average_upperlimit": conf.TEST_VALUE
                    }
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        network_helper.remove_qos_from_dc(qos_name=cls.qos_name)
        super(TestSanity03, cls).teardown_class()


class TestSanity04(TestSanityCaseBase):
    """
    Test MTU over VM/Non-VM/VLAN and BOND
    """

    __test__ = True
    net = conf.NETS[4]
    bond = "bond41"

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
        helper.send_setup_networks(sn_dict=mtu_over_vm_dict)

    def test_mtu_over_non_vm(self):
        """
        Create network with MTU 5000 over Non-VM network
        """
        mtu_over_non_vm_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[1]
                }
            }
        }
        helper.send_setup_networks(sn_dict=mtu_over_non_vm_dict)

    def test_mtu_over_vlan(self):
        """
        Create network with MTU 5000 over VLAN network
        """
        mtu_over_vlan_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[2]
                }
            }
        }
        helper.send_setup_networks(sn_dict=mtu_over_vlan_dict)

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
        helper.send_setup_networks(sn_dict=mtu_over_bond_dict)

    @classmethod
    def tearDown(cls):
        """
        Clean host interfaces
        """
        super(TestSanity04, cls).teardown_class()


class TestSanity05(TestSanityCaseBase):
    """
    Test bridgeless network with VLAN/No-VLAN over NIC/BOND
    """

    __test__ = True
    net = conf.NETS[5]
    bond_1 = "bond51"
    bond_2 = "bond52"

    def test_bridgless_on_nic(self):
        """
        Attach bridgeless network on NIC
        """
        bridgeless_on_nic_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[0]
                }
            }
        }
        helper.send_setup_networks(sn_dict=bridgeless_on_nic_dict)

    def test_bridgeless_vlan_on_nic(self):
        """
        Attach bridgeless network with VLAN on NIC
        """
        bridgeless_vlan_on_nic_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[1]
                }
            }
        }
        helper.send_setup_networks(sn_dict=bridgeless_vlan_on_nic_dict)

    def test_bridgeless_on_bond(self):
        """
        Attach bridgeless network on BOND
        """
        bridgeless_on_bond_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": conf.DUMMYS[:2]
                },
                "2": {
                    "nic": self.bond_1,
                    "network": self.net[2]
                }
            }
        }
        helper.send_setup_networks(sn_dict=bridgeless_on_bond_dict)

    def test_bridgeless_vlan_over_bond(self):
        """
        Attach bridgeless VLAN network on BOND
        """
        bridgeless_vlan_on_bond_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "slaves": conf.DUMMYS[2:4]
                },
                "2": {
                    "nic": self.bond_2,
                    "network": self.net[3]
                }
            }
        }
        helper.send_setup_networks(sn_dict=bridgeless_vlan_on_bond_dict)

    @classmethod
    def tearDown(cls):
        """
        Clean host interfaces
        """
        super(TestSanity05, cls).teardown_class()


class TestSanity06(TestSanityCaseBase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True
    nets = conf.NETS[6]

    @classmethod
    def setup_class(cls):
        """
        Create 5 VNICs on VM with different params for plugged/linked
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.nets[0]
                },
                "2": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.nets[1]
                },
                "3": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.nets[2]
                },
                "4": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.nets[3]
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)
        helper.run_vm_on_host()
        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [
            ("true", "true"),
            ("true", "false"),
            ("false", "true"),
            ("false", "false")
        ]
        for i in range(len(plug_link_param_list)):
            nic_name = conf.NIC_NAME[i+1]
            if not ll_vms.addNic(
                positive=True, vm=conf.VM_0, name=nic_name,
                network=cls.nets[i], plugged=plug_link_param_list[i][0],
                linked=plug_link_param_list[i][1]
            ):
                raise conf.NET_EXCEPTION(
                    "Cannot add VNIC %s to %s" % (nic_name, conf.VM_0)
                )
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_0, name=conf.NIC_NAME[5], network=None,
            plugged="true", linked="true"
        ):
            raise conf.NET_EXCEPTION(
                "Cannot add VNIC %s to %s" % (conf.NIC_NAME[5], conf.VM_0)
            )

    @polarion("RHEVM3-3829")
    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        for nic_name in (
            conf.NIC_NAME[1], conf.NIC_NAME[3], conf.NIC_NAME[5]
        ):
            logger.info("Check that linked status on %s in True", nic_name)
            if not ll_vms.getVmNicLinked(vm=conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION(
                    "NIC %s is not linked but should be" % nic_name
                )
        for nic_name in (
            conf.NIC_NAME[1], conf.NIC_NAME[2], conf.NIC_NAME[5]
        ):
            logger.info("Check that plugged status on %s in True", nic_name)
            if not ll_vms.getVmNicPlugged(vm=conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION(
                    "NIC %s is not plugged but should be" % nic_name
                )
        for nic_name in (conf.NIC_NAME[2], conf.NIC_NAME[4]):
            logger.info("Check that linked status on %s in False", nic_name)
            if ll_vms.getVmNicLinked(vm=conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION(
                    "NIC %s is linked but shouldn't be" % nic_name
                )
        for nic_name in (conf.NIC_NAME[3], conf.NIC_NAME[4]):
            logger.info("Check that plugged status on %s in False", nic_name)
            if ll_vms.getVmNicPlugged(vm=conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION(
                    "NIC %s is plugged but shouldn't be" % nic_name
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        helper.stop_vm()
        logger.info("Removing all the VNICs besides management network")
        for i in range(5):
            nic_name = conf.NIC_NAME[i+1]
            if not ll_vms.removeNic(
                positive=True, vm=conf.VM_0, nic=nic_name
            ):
                logger.error("Cannot remove nic %s from setup", nic_name)
        super(TestSanity06, cls).teardown_class()
