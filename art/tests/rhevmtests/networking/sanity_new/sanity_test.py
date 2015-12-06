#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.core_api import apis_utils
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import rhevmtests.networking.mgmt_net_role.helper as mgmt_net_helper
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.mac_pool_range_per_dc.helper as mac_pool_helper
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
        network_helper.is_network_in_vds_caps(
            host_resource=conf.VDS_HOST_0, network=self.bridge_name
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
    qos_name = conf.QOS_NAME[3][0]
    net = conf.NETS[3][0]

    @polarion("RHEVM3-6525")
    @bz({"1274187": {"engine": None, "version": ["3.6"]}})
    def test_add_network_qos(self):
        """
        Create new Host Network QoS profile under DC
        """
        network_helper.create_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.QOS_TEST_VALUE
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
                        "outbound_average_linkshare": conf.QOS_TEST_VALUE,
                        "outbound_average_realtime": conf.QOS_TEST_VALUE,
                        "outbound_average_upperlimit": conf.QOS_TEST_VALUE
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
        for nic in conf.NIC_NAME[1:6]:
            if not ll_vms.removeNic(positive=True, vm=conf.VM_0, nic=nic):
                logger.error("Cannot remove nic %s from setup", nic)
        super(TestSanity06, cls).teardown_class()


@unittest_lib.attr(tier=1)
class TestSanity07(unittest_lib.NetworkTest):
    """
    1. Create a new DC and check it was created with updated Default
    MAC pool values
    2. Extend the default range values of Default MAC pool
    3. Add new ranges to the Default MAC pool
    4. Remove added ranges from the Default MAC pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create DC
        """
        mac_pool_helper.create_dc(mac_pool_name="")

    def test_check_default_mac_new_dc(self):
        """
        Check default MAC pool
        """
        logger.info(
            "Check that the new DC was created with default MAC pool"
        )
        if not (
                ll_mac_pool.get_default_mac_pool().get_id() ==
                ll_mac_pool.get_mac_pool_from_dc(conf.EXT_DC_1).get_id()
        ):
            raise conf.NET_EXCEPTION(
                "New DC was not created with the default MAC pool values"
            )

    def test_extend_default_mac_range(self):
        """
        Extend the default range values of Default MAC pool
        """
        logger.info("Extend the default MAC pool range")
        mac_pool_helper.update_mac_pool_range_size(
            mac_pool_name=conf.DEFAULT_MAC_POOL, size=(2, 2)
        )

    def test_01_add_new_range(self):
        """
        Add new ranges to the Default MAC pool
        """
        logger.info("Add new ranges to the Default MAC pool")
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=conf.DEFAULT_MAC_POOL,
            range_list=conf.MAC_POOL_RANGE_LIST
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add ranges to the Default MAC Pool"
            )

    def test_02_remove_new_added_range(self):
        """
        Remove added ranges from the Default MAC pool
        """
        logger.info("Remove added ranges from the Default MAC pool")
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=conf.DEFAULT_MAC_POOL,
            range_list=conf.MAC_POOL_RANGE_LIST
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove the ranges from the Default MAC pool"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        mac_pool_helper.remove_dc()


class TestSanity08(TestSanityCaseBase):
    """
    Create new DC and cluster with non default management network
    Prepare networks on new DC
    Create new DC and cluster with default management network
    """
    __test__ = True
    net = conf.NETS[8][0]
    dc = conf.EXT_DC_0
    cluster_1 = conf.EXTRA_CL[0]
    cluster_2 = conf.EXTRA_CL[1]

    @classmethod
    def setup_class(cls):
        """
        Create new DC
        """
        net_dict = {
            cls.net: {
                "required": "true",
            }
        }
        mgmt_net_helper.create_setup(dc=cls.dc)
        network_helper.prepare_networks_on_setup(
            networks_dict=net_dict, dc=cls.dc,
        )

    def test_create_dc_cluster_with_management_net(self):
        """
        Create new DC and cluster with non default management network
        """
        logger.info(
            "Create %s with %s as management network", self.cluster_1, self.net
        )
        mgmt_net_helper.add_cluster(
            cl=self.cluster_1, dc=self.dc, management_network=self.net
        )
        mgmt_net_helper.check_mgmt_net(cl=self.cluster_1, net=self.net)

    def test_create_dc_cluster_with_default_management_net(self):
        """
        Create new DC and cluster with default management network
        """
        logger.info("Create %s", self.cluster_2)
        mgmt_net_helper.add_cluster(
            cl=self.cluster_2, dc=self.dc, management_network=conf.MGMT_BRIDGE
        )
        mgmt_net_helper.check_mgmt_net(cl=self.cluster_2, net=conf.MGMT_BRIDGE)

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and clusters
        """
        for cl in (cls.cluster_1, cls.cluster_2):
            mgmt_net_helper.remove_cl(cl=cl)
        mac_pool_helper.remove_dc(dc_name=cls.dc)
        super(TestSanity08, cls).teardown_class()


class TestSanity09(TestSanityCaseBase):
    """
    Attach VM non-VLAN network with MTU 9000 to host NIC
    Change the network MTU
    Change the network to be tagged
    Change the network to be non-VM network
    """
    __test__ = True
    net = conf.NETS[9][0]
    dc = conf.DC_0_NAME

    @classmethod
    def setup_class(cls):
        """
        Attach VM non-VLAN network with MTU 9000 to host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.net
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)

    def test_change_mtu(self):
        """
        Change the network MTU
        """
        mtu = conf.MTU[-1]
        mtu_dict = {
            "mtu": mtu
        }
        logger.info("Update %s with MTU %s", self.net, mtu)
        if not ll_networks.updateNetwork(
            positive=True, network=self.net, data_center=self.dc, mtu=mtu
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update %s with MTU %s" % (self.net, mtu)
            )
        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_networks.checkHostNicParameters, host=conf.HOST_NAME_0,
            nic=conf.HOST_0_NICS[1], **mtu_dict
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Couldn't get correct MTU (%s) on host NIC %s" %
                (mtu, conf.HOST_0_NICS[1])
            )
        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s",
            self.net, conf.HOST_NAME_0
        )
        if not test_utils.checkMTU(
            host=conf.HOST_0_IP, user=conf.HOSTS_USER, password=conf.HOSTS_PW,
            mtu=mtu, physical_layer=False, network=self.net,
            nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Logical layer: %s MTU should be %s" % (self.net, mtu)
            )
        logger.info(
            "Checking physical layer of bridged network %s on host %s",
            self.net, conf.HOST_NAME_0
        )
        if not test_utils.checkMTU(
            host=conf.HOST_0_IP, user=conf.HOSTS_USER, password=conf.HOSTS_PW,
            mtu=mtu, nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Physical layer: %s MTU should be %s" %
                (conf.HOST_0_NICS[1], mtu)
            )

    def test_change_vlan(self):
        """
        Change the network VLAN
        """
        vlan_id = conf.VLAN_IDS[11]
        vlan_dict = {"vlan_id": vlan_id}
        logger.info("Update %s with VLAN %s", self.net, vlan_id)
        if not ll_networks.updateNetwork(
            positive=True, network=self.net, data_center=self.dc,
            vlan_id=vlan_id
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update %s to be tagged with VLAN %s"
                % (self.net, vlan_id)
            )
        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_networks.checkHostNicParameters, host=conf.HOST_NAME_0,
            nic=conf.HOST_0_NICS[1], **vlan_dict
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "%s.%s doesn't exist on %s" %
                (self.net, vlan_id, conf.HOST_NAME_0)
            )
        logger.info("Check that the change is reflected to Host")
        if not ll_networks.checkVlanNet(
            host=conf.HOST_0_IP, user=conf.HOSTS_USER, password=conf.HOSTS_PW,
            interface=conf.HOST_0_NICS[1], vlan=vlan_id
        ):
            raise conf.NET_EXCEPTION(
                "%s on host %s was not updated with correct VLAN %s"
                % (self.net, conf.HOST_NAME_0, vlan_id)
            )

    def test_change_to_non_vm(self):
        """
        Change the network to be non-VM network
        """
        bridge_dict = {"bridge": False}
        logger.info("Update network %s to be non-VM network", self.net)
        if not ll_networks.updateNetwork(
            positive=True, network=self.net, data_center=self.dc,
            usages=""
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update %s to be non-VM network" % self.net
            )
        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_networks.checkHostNicParameters, host=conf.HOST_NAME_0,
            nic=conf.HOST_0_NICS[1], **bridge_dict
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "%s is VM network and should be Non-VM" % self.net
            )
        logger.info("Check that the change is reflected to Host")
        if ll_networks.isVmHostNetwork(
            host=conf.HOST_0_IP, user=conf.HOSTS_USER, password=conf.HOSTS_PW,
            net_name=self.net, conn_timeout=45
        ):
            raise conf.NET_EXCEPTION(
                "%s on host %s was not updated to be non-VM network"
                % (self.net, conf.HOST_NAME_0)
            )
