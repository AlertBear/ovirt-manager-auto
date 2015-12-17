#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.core_api import apis_utils, apis_exceptions
from art.rhevm_api.utils import test_utils
import rhevmtests.helpers as global_helper
import art.unittest_lib.network as lib_network
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import rhevmtests.networking.management_as_role.helper as mgmt_net_helper
import rhevmtests.networking.multiple_queue_nics.helper as queue_helper
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.mac_pool_range_per_dc.helper as mac_pool_helper
import rhevmtests.networking.arbitrary_vlan_device_name.helper as vlan_helper
import rhevmtests.networking.required_network.helper as required_network_helper

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

    @polarion("RHEVM3-14499")
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

    @polarion("RHEVM3-14500")
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

    @polarion("RHEVM3-14501")
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

    @polarion("RHEVM3-14502")
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

    @polarion("RHEVM3-14503")
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

    @polarion("RHEVM3-14504")
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

    @polarion("RHEVM3-14505")
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

    @polarion("RHEVM3-14506")
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

    @polarion("RHEVM3-14507")
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

    @polarion("RHEVM3-14509")
    def test_extend_default_mac_range(self):
        """
        Extend the default range values of Default MAC pool
        """
        logger.info("Extend the default MAC pool range")
        mac_pool_helper.update_mac_pool_range_size(
            mac_pool_name=conf.DEFAULT_MAC_POOL, size=(2, 2)
        )

    @polarion("RHEVM3-14510")
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

    @polarion("RHEVM3-14511")
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

    @polarion("RHEVM3-14512")
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

    @polarion("RHEVM3-14513")
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

    @polarion("RHEVM3-14515")
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

    @polarion("RHEVM3-14516")
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
        if not ll_networks.is_vlan_on_host_network(
            vds_resource=conf.VDS_HOST_0, interface=conf.HOST_0_NICS[1],
            vlan=vlan_id
        ):
            raise conf.NET_EXCEPTION(
                "%s on host %s was not updated with correct VLAN %s"
                % (self.net, conf.HOST_NAME_0, vlan_id)
            )

    @polarion("RHEVM3-14517")
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
        if ll_networks.is_host_network_is_vm(
            vds_resource=conf.VDS_HOST_0, net_name=self.net
        ):
            raise conf.NET_EXCEPTION(
                "%s on host %s was not updated to be non-VM network"
                % (self.net, conf.HOST_NAME_0)
            )


@unittest_lib.attr(tier=1)
class TestSanity10(unittest_lib.NetworkTest):
    """
    Verify you can configure additional network beside management with gateway
    Verify you can remove network configured with gateway
    """
    __test__ = True
    ip = conf.MG_IP_ADDR
    gateway = conf.MG_GATEWAY
    netmask = conf.NETMASK
    subnet = conf.SUBNET
    net = conf.NETS[10][0]

    @classmethod
    def setup_class(cls):
        """
        Attach VM network with IP and gateway to host
        """
        ip_addr_dict = {
            "ip_gateway": {
                "address": cls.ip,
                "netmask": cls.netmask,
                "boot_protocol": "static",
                "gateway": cls.gateway
            }
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": cls.net,
                    "ip": ip_addr_dict
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)

    @polarion("RHEVM3-3949")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.check_ip_rule(
            host_resource=conf.VDS_HOST_0, subnet=self.subnet
        ):
            raise conf.NET_EXCEPTION(
                "Incorrect gateway configuration for %s" % self.net
            )

    @polarion("RHEVM3-3965")
    def test_detach_gw_net(self):
        """
        Remove network with gw configuration from setup
        """
        network_host_api_dict = {
            "remove": {
                "networks": [self.net]
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)


@unittest_lib.attr(tier=1)
class TestSanity11(unittest_lib.NetworkTest):
    """
    Configure queue on existing network
    """
    __test__ = True
    vm = conf.VM_0
    num_queues = conf.NUM_QUEUES[0]
    prop_queue = conf.PROP_QUEUES[0]
    dc = conf.DC_0_NAME

    @classmethod
    def setup_class(cls):
        """
        Configure and update queue value on vNIC profile for existing network
        (vNIC CustomProperties)
        Start VM
        """
        logger.info(
            "Update custom properties on %s to %s", conf.MGMT_BRIDGE,
            cls.prop_queue
        )
        if not ll_networks.updateVnicProfile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=cls.dc, custom_properties=cls.prop_queue
        ):
            raise conf.NET_EXCEPTION(
                "Failed to set custom properties on %s" % conf.MGMT_BRIDGE
            )
        logger.info("Start %s", cls.vm)
        if not ll_vms.startVm(positive=True, vm=cls.vm, wait_for_ip=True):
            raise conf.NET_EXCEPTION("Failed to start %s" % cls.vm)

    @polarion("RHEVM3-4309")
    def test_multiple_queue_nics(self):
        """
        Check that queue exists in qemu process, vdsm.log and engine.log
        """
        host_resource = global_helper.get_host_resource_of_running_vm(
            vm=self.vm
        )
        logger.info("Check that qemu has %s queues", self.num_queues)
        if not queue_helper.check_queues_from_qemu(
            vm=self.vm, host_obj=host_resource, num_queues=self.num_queues
        ):
            raise conf.NET_EXCEPTION(
                "qemu did not return the expected number of queues"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove custom properties with queues from management vNIC profile
        Stop VM
        """
        logger.info("Remove custom properties on %s", conf.MGMT_BRIDGE)
        if not ll_networks.updateVnicProfile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=cls.dc, custom_properties="clear"
        ):
            logger.error(
                "Failed to remove custom properties from %s", conf.MGMT_BRIDGE
            )
        logger.info("Stop %s", cls.vm)
        if not ll_vms.stopVm(positive=True, vm=cls.vm):
            logger.error("Failed to stop %s", cls.cm)


class TestSanity12(TestSanityCaseBase):
    """
    Attach network with bridge_opts and ethtool_opts to host NIC
    """
    __test__ = True
    net = conf.NETS[12][0]

    @polarion("RHEVM3-10478")
    def test_network_custom_properties_on_host(self):
        """
        Attach network with bridge_opts and ethtool_opts to host NIC
        """
        properties_dict = {
            "bridge_opts": conf.PRIORITY,
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "properties": properties_dict
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            self.net, conf.HOST_0_NICS[1], conf.HOST_NAME_0
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_NAME_0, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    self.net, conf.HOST_0_NICS[1], conf.HOST_NAME_0
                )
            )


@unittest_lib.attr(tier=1)
class TestSanity13(unittest_lib.NetworkTest):
    """
    Check that Network Filter is enabled by default
    """
    __test__ = True
    vm = conf.VM_0
    host_resource = None

    @classmethod
    def setup_class(cls):
        """
        Start VM
        Get host resource where VM is running
        """
        logger.info("Start %s", cls.vm)
        if not ll_vms.startVm(positive=True, vm=cls.vm, wait_for_ip=True):
            raise conf.NET_EXCEPTION("Failed to start %s" % cls.vm)

        cls.host_resource = global_helper.get_host_resource_of_running_vm(
            vm=cls.vm
        )

    @polarion("RHEVM3-3775")
    def test_check_filter_status_engine(self):
        """
        Check that Network Filter is enabled by default on engine
        """
        logger.info("Check that Network Filter is enabled on engine")
        if not test_utils.checkSpoofingFilterRuleByVer(
            host=conf.VDC_HOST, user=conf.VDC_ROOT_USER,
            passwd=conf.VDC_ROOT_PASSWORD
        ):
            raise conf.NET_EXCEPTION("Network Filter is disabled on engine")

    @polarion("RHEVM3-3777")
    def test_check_filter_status_vdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        logger.info("Check that Network Filter is enabled on VDSM")
        if not ll_hosts.checkNetworkFiltering(
            positive=True, host=self.host_resource.ip, user=conf.HOSTS_USER,
            passwd=conf.HOSTS_PW
        ):
            raise conf.NET_EXCEPTION("Network Filter is disabled on VDSM")

    @polarion("RHEVM3-3779")
    def test_check_filter_status_dump_xml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        logger.info("Check that Network Filter is enabled via dumpxml")
        if not ll_hosts.checkNetworkFilteringDumpxml(
            positive=True, host=self.host_resource.ip, user=conf.HOSTS_USER,
            passwd=conf.HOSTS_PW, vm=self.vm, nics="1"
        ):
            raise conf.NET_EXCEPTION("Network Filter is disabled via dumpxml")

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        """
        logger.info("Stop %s", cls.vm)
        if not ll_vms.stopVm(positive=True, vm=cls.vm):
            logger.error("Failed to stop %s", cls.vm)


class TestSanity14(TestSanityCaseBase):
    """
    Attach VLAN and VM networks to NIC and BOND via labels
    """
    __test__ = True
    net_1_nic = conf.NETS[14][0]
    net_2_nic_vlan = conf.NETS[14][1]
    net_3_bond = conf.NETS[14][2]
    net_4_bond_vlan = conf.NETS[14][3]
    lb_1 = conf.LABEL_LIST[0]
    lb_2 = conf.LABEL_LIST[1]
    bond = "bond14"

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        Add lb_1 and lb_2 to VM and VLAN networks
        """
        logger.info("Create %s on %s", cls.bond, conf.HOST_NAME_0)
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)
        logger.info(
            "Attach %s label to %s and %s",
            cls.lb_1, cls.net_1_nic, cls.net_2_nic_vlan
        )
        if not ll_networks.add_label(
            label=cls.lb_1, networks=[cls.net_1_nic, cls.net_2_nic_vlan]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s and %s" %
                (cls.lb_1, cls.net_1_nic, cls.net_2_nic_vlan)
            )
        logger.info(
            "Attach %s label to %s and %s",
            cls.lb_2, cls.net_3_bond, cls.net_4_bond_vlan
        )
        if not ll_networks.add_label(
            label=cls.lb_2, networks=[cls.net_3_bond, cls.net_4_bond_vlan]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s and %s" %
                (cls.lb_2, cls.net_3_bond, cls.net_4_bond_vlan)
            )

    @polarion("RHEVM3-13511")
    def test_label_nic_vm_vlan(self):
        """
        Check that untagged VM and VLAN networks are attached to the Host NIC
        via labels
        """
        vlan_nic = lib_network.vlan_int_name(
            conf.HOST_0_NICS[1], conf.VLAN_IDS[12]
        )
        logger.info(
            "Attach label %s to host NIC %s ", self.lb_1, conf.HOST_0_NICS[1]
        )
        if not ll_networks.add_label(
            label=self.lb_1,
            host_nic_dict={
                conf.HOST_NAME_0: [conf.HOST_0_NICS[1]]
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to host NIC %s" %
                (self.lb_1, conf.HOST_0_NICS[1])
            )
        for net in (self.net_1_nic, self.net_2_nic_vlan):
            logger.info(
                "Check that network %s is attached to host NIC %s",
                net, conf.HOST_0_NICS[1]
            )
            host_nic = (
                vlan_nic if net == self.net_2_nic_vlan else
                conf.HOST_0_NICS[1]
            )
            if not ll_networks.check_network_on_nic(
                network=net, host=conf.HOST_NAME_0, nic=host_nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to host NIC %s " %
                    (net, conf.HOST_0_NICS[1])
                )

    @polarion("RHEVM3-13894")
    def test_label_bond_vm_vlan(self):
        """
        Check that the untagged VM and VLAN networks are attached to BOND via
        labels
        """
        vlan_bond = lib_network.vlan_int_name(self.bond, conf.VLAN_IDS[13])
        logger.info("Attach label %s to bond %s ", self.lb_2, self.bond)
        if not ll_networks.add_label(
            label=self.lb_2, host_nic_dict={
                conf.HOST_NAME_0: [self.bond]
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to bond %s" % (self.lb_2, self.bond)
            )
        for net in (self.net_3_bond, self.net_4_bond_vlan):
            logger.info(
                "Check that network %s is attached to bond %s", net, self.bond
            )
            bond = (
                vlan_bond if net == self.net_4_bond_vlan else self.bond
            )
            if not ll_networks.check_network_on_nic(
                network=net, host=conf.HOST_NAME_0, nic=bond
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to bond %s " % (net, self.bond)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        err = "Couldn't remove %s label from %s" % (cls.lb_2, cls.bond)
        logger.info("Removing %s label from %s", cls.lb_2, cls.bond)
        try:
            if not ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_NAME_0: [cls.bond]
                }
            ):
                logger.error(err)
        except apis_exceptions.EntityNotFound:
            logger.error(err)
        super(TestSanity14, cls).teardown_class()


class TestSanity15(TestSanityCaseBase):
    """
    Set network as required
    Set the network host NIC down
    Check that host status is non-operational
    """
    __test__ = True
    net = conf.NETS[15][0]

    @classmethod
    def setup_class(cls):
        """
        Deactivate all hosts beside the first one
        Attach required network to host
        Set the network host NIC down
        """
        required_network_helper.deactivate_hosts()
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)
        logger.info("Set %s down", conf.HOST_0_NICS[1])
        if not ll_hosts.ifdownNic(
            host=conf.HOST_0_IP, root_password=conf.HOSTS_PW,
            nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Failed to set down %s" % conf.HOST_0_NICS[1]
            )

    @polarion("RHEVM3-3750")
    def test_non_operational(self):
        """
        Check that Host is non-operational
        """
        logger.info("Check that %s is non-operational", conf.HOST_NAME_0)
        if not ll_hosts.waitForHostsStates(
            positive=True, names=conf.HOST_NAME_0, states="non_operational",
            timeout=conf.TIMEOUT * 2
        ):
            raise conf.NET_EXCEPTION(
                "%s status is not non-operational" % conf.HOST_NAME_0
            )

    @classmethod
    def teardown_class(cls):
        """
        Activate all hosts
        """
        required_network_helper.activate_hosts()
        super(TestSanity15, cls).teardown_class()


class TestSanity16(TestSanityCaseBase):

    """
    Create new vNIC profile and make sure all its parameters exist in API
    """
    __test__ = True
    net = conf.NETS[16][0]
    dc = conf.DC_0_NAME
    vnic_profile = conf.VNIC_PROFILES[16][0]
    description = "vnic_profile_test"

    @classmethod
    def setup_class(cls):
        """
        Attach network to host
        Create additional vNIC profile with description and port mirroring
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        helper.send_setup_networks(sn_dict=network_host_api_dict)
        if not ll_networks.addVnicProfile(
            positive=True, name=cls.vnic_profile, data_center=cls.dc,
            network=cls.net, port_mirroring=True, description=cls.description
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't create second VNIC profile %s for %s" %
                (cls.vnic_profile, cls.net)
            )

    @polarion("RHEVM3-3970")
    def test_check_attr_vnic_profile(self):
        """
        Check vNIC profile was created with description, port mirroring and
        name
        """
        attr_dict = ll_networks.getVnicProfileAttr(
            name=self.vnic_profile, network=self.net,
            attr_list=["description", "port_mirroring", "name"]
        )
        if (
                attr_dict.get("description") != self.description or
                attr_dict.get("port_mirroring") is not True or
                attr_dict.get("name") != self.vnic_profile
        ):
            raise conf.NET_EXCEPTION(
                "Attributes are not equal to what was set"
            )
