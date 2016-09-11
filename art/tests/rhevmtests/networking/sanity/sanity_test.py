#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sanity_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.multiple_gateways.config as multiple_gw_conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.mac_pool_range_per_dc.config as mac_pool_conf
import rhevmtests.networking.mac_pool_range_per_dc.helper as mac_pool_helper
import rhevmtests.networking.management_as_role.helper as mgmt_net_helper
import rhevmtests.networking.multiple_queue_nics.config as multiple_queue_conf
import rhevmtests.networking.network_custom_properties.config as custom_pr_conf
import rhevmtests.networking.network_filter.config as nf_conf
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    add_vnic_profile, create_networks, clean_host_interfaces,
    remove_qos, attach_networks, update_vnic_profile, start_vm,
    case_06_fixture, case_07_fixture, case_08_fixture, add_labels,
    deactivate_hosts, set_host_nic_down
)


@attr(tier=1)
class TestSanityCaseBase(NetworkTest):
    """
    Base class for sanity cases
    """
    pass


@pytest.mark.usefixtures(
    create_networks.__name__,
    add_vnic_profile.__name__
)
class TestSanity01(TestSanityCaseBase):
    """
    Create new vNIC profile and make sure all its parameters exist in API
    """
    __test__ = True
    net = sanity_conf.NETS[1][0]
    nic = 1
    dc = conf.DC_0
    vnic_profile = sanity_conf.VNIC_PROFILES[1][0]
    description = "vnic_profile_test"

    @polarion("RHEVM3-3970")
    def test_check_attr_vnic_profile(self):
        """
        Check vNIC profile was created with description, port mirroring and
        name
        """
        testflow.step(
            "Check vNIC profile was created with description, port mirroring "
            "and name"
        )
        attr_dict = ll_networks.get_vnic_profile_attr(
            name=self.vnic_profile, network=self.net,
            attr_list=["description", "port_mirroring", "name"]
        )
        assert attr_dict.get("description") == self.description
        assert attr_dict.get("port_mirroring") is True
        assert attr_dict.get("name") == self.vnic_profile


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__
)
@pytest.mark.incremental
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
    net = sanity_conf.NETS[2]
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    bond_4 = "bond24"

    @polarion("RHEVM3-9850")
    def test_01_multiple_actions(self):
        """
        Attach Non-VM + 2 VLAN networks (IP and custom properties) to NIC1
        Create BOND and attach Non-VM + 1 VLAN network with IP to BOND
        Create empty BOND
        """
        properties_dict = {
            "bridge_opts": custom_pr_conf.PRIORITY,
            "ethtool_opts": custom_pr_conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[2], state="off"
            )
        }
        sn_dict = {
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
                    "ip": sanity_conf.BASIC_IP_DICT_PREFIX,
                    "properties": properties_dict
                },
                "4": {
                    "nic": self.bond_1,
                    "slaves": conf.HOST_0_NICS[2:4]
                },
                "5": {
                    "nic": self.bond_1,
                    "network": self.net[3],
                    "ip": sanity_conf.BASIC_IP_DICT_NETMASK
                },
                "6": {
                    "nic": self.bond_1,
                    "network": self.net[4],
                },
                "7": {
                    "nic": self.bond_2,
                    "slaves": conf.HOST_0_NICS[4:6]
                },
                "8": {
                    "nic": self.bond_3,
                    "slaves": conf.HOST_0_NICS[6:9]
                },
                "9": {
                    "nic": self.bond_4,
                    "slaves": conf.HOST_0_NICS[9:11]
                }

            }
        }
        testflow.step(
            "Create: Attach Non-VM + 2 VLAN networks (IP and custom "
            "properties) to NIC1. "
            "Create BOND and attach Non-VM + 1 VLAN network with IP to BOND. "
            "Create empty BOND"
        )
        assert hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict)

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
        sn_dict = {
            "update": {
                "1": {
                    "nic": self.bond_1,
                    "network": self.net[1],
                },
                "2": {
                    "nic": conf.HOST_0_NICS[11],
                    "network": self.net[2],
                    "ip": sanity_conf.BASIC_IP_DICT_PREFIX
                },
                "3": {
                    "nic": self.bond_2,
                    "network": self.net[4],
                },
                "4": {
                    "nic": self.bond_2,
                    "slaves": [conf.HOST_0_NICS[12]]
                },
                "5": {
                    "nic": self.bond_3,
                    "slaves": [conf.HOST_0_NICS[8]]
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
        testflow.step(
            "Update:Move network from NIC to existing BOND"
            "Change NIC for existing network"
            "Add slave to existing BOND and Move network from another BOND to "
            "it"
            "Create new BOND with network attached to it"
            "Remove network from NIC"
            "Remove network from BOND"
            "Remove BOND"
        )
        assert hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict)


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    remove_qos.__name__,
    create_networks.__name__
)
class TestSanity03(TestSanityCaseBase):
    """
    Add new network QOS (named)
    Attach network with QoS to host NIC
    """
    __test__ = True
    qos_name = sanity_conf.QOS_NAME[3][0]
    net = sanity_conf.NETS[3][0]

    @polarion("RHEVM3-6525")
    def test_add_network_qos(self):
        """
        Create new Host Network QoS profile under DC
        """
        testflow.step("Create new Host Network QoS profile under DC")
        assert network_helper.create_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.QOS_TEST_VALUE
        )

    @polarion("RHEVM3-6526")
    @bz({"1329224": {}})
    def test_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        sn_dict = {
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
        testflow.step(
            "Attach network to host NIC with QoS parameters (Anonymous' QoS)"
        )
        hl_host_network.setup_networks(host_name=conf.HOST_0_NAME, **sn_dict)


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__
)
class TestSanity04(TestSanityCaseBase):
    """
    Test MTU over VM/Non-VM/VLAN and BOND
    """
    __test__ = True
    net = sanity_conf.NETS[4]
    bond = "bond41"

    @polarion("RHEVM3-14499")
    def test_mtu_over_vm(self):
        """
        Create network with MTU 5000 over VM network
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[0]
                }
            }
        }
        testflow.step("Create network with MTU 5000 over VM network")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14500")
    def test_mtu_over_non_vm(self):
        """
        Create network with MTU 5000 over Non-VM network
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[2],
                    "network": self.net[1]
                }
            }
        }
        testflow.step("Create network with MTU 5000 over Non-VM network")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14501")
    def test_mtu_over_vlan(self):
        """
        Create network with MTU 5000 over VLAN network
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[3],
                    "network": self.net[2]
                }
            }
        }
        testflow.step("Create network with MTU 5000 over VLAN network")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14502")
    def test_mtu_over_bond(self):
        """
        Create network with MTU 5000 over BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": self.bond,
                    "slaves": conf.HOST_0_NICS[4:6]
                },
                "2": {
                    "nic": self.bond,
                    "network": self.net[3]
                }
            }
        }
        testflow.step("Create network with MTU 5000 over BOND")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__
)
class TestSanity05(TestSanityCaseBase):
    """
    Test bridgeless network with VLAN/No-VLAN over NIC/BOND
    """
    __test__ = True
    net = sanity_conf.NETS[5]
    bond_1 = "bond51"
    bond_2 = "bond52"

    @polarion("RHEVM3-14503")
    def test_bridgless_on_nic(self):
        """
        Attach bridgeless network on NIC
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[0]
                }
            }
        }
        testflow.step("Attach bridgeless network on NIC")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14504")
    def test_bridgeless_vlan_on_nic(self):
        """
        Attach bridgeless network with VLAN on NIC
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": conf.HOST_0_NICS[1],
                    "network": self.net[1]
                }
            }
        }
        testflow.step("Attach bridgeless network with VLAN on NIC")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14505")
    def test_bridgeless_on_bond(self):
        """
        Attach bridgeless network on BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": self.bond_1,
                    "slaves": conf.HOST_0_NICS[2:4]
                },
                "2": {
                    "nic": self.bond_1,
                    "network": self.net[2]
                }
            }
        }
        testflow.step("Attach bridgeless network on BOND")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

    @polarion("RHEVM3-14506")
    def test_bridgeless_vlan_over_bond(self):
        """
        Attach bridgeless VLAN network on BOND
        """
        sn_dict = {
            "add": {
                "1": {
                    "nic": self.bond_2,
                    "slaves": conf.HOST_0_NICS[4:6]
                },
                "2": {
                    "nic": self.bond_2,
                    "network": self.net[3]
                }
            }
        }
        testflow.step("Attach bridgeless VLAN network on BOND")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__,
    attach_networks.__name__,
    case_06_fixture.__name__,
    start_vm.__name__
)
class TestSanity06(TestSanityCaseBase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True
    nets = sanity_conf.NETS[6][:4]
    nic = 1
    vm = conf.VM_0
    ip = None
    ip_addr_dict = None
    bond = None

    @polarion("RHEVM3-3829")
    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        testflow.step(
            "Check all permutation for the Plugged/Linked options on VNIC"
        )
        for nic_name in (
            conf.NIC_NAME[1], conf.NIC_NAME[3], conf.NIC_NAME[5]
        ):
            assert ll_vms.get_vm_nic_linked(vm=self.vm, nic=nic_name)

        for nic_name in (
            conf.NIC_NAME[1], conf.NIC_NAME[2], conf.NIC_NAME[5]
        ):
            assert ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic_name)

        for nic_name in (conf.NIC_NAME[2], conf.NIC_NAME[4]):
            assert not ll_vms.get_vm_nic_linked(vm=self.vm, nic=nic_name)

        for nic_name in (conf.NIC_NAME[3], conf.NIC_NAME[4]):
            assert not ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic_name)


@bz({"1344284": {}})
@pytest.mark.usefixtures(case_07_fixture.__name__)
class TestSanity07(TestSanityCaseBase):
    """
    1. Create a new DC and check it was created with updated Default
    MAC pool values
    2. Extend the default range values of Default MAC pool
    3. Add new ranges to the Default MAC pool
    4. Remove added ranges from the Default MAC pool
    """
    __test__ = True
    ext_dc = mac_pool_conf.EXT_DC_1

    @polarion("RHEVM3-14507")
    def test_check_default_mac_new_dc(self):
        """
        Check default MAC pool
        """
        testflow.step(
            "Check that the new DC was created with default MAC pool"
        )
        default_mac_id = ll_mac_pool.get_default_mac_pool().get_id()
        ext_dc_mac_id = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc).get_id()
        assert default_mac_id == ext_dc_mac_id

    @polarion("RHEVM3-14509")
    def test_extend_default_mac_range(self):
        """
        Extend the default range values of Default MAC pool
        """
        testflow.step("Extend the default range values of Default MAC pool")
        assert mac_pool_helper.update_mac_pool_range_size(
            mac_pool_name=mac_pool_conf.DEFAULT_MAC_POOL, size=(2, 2)
        )

    @polarion("RHEVM3-14510")
    def test_01_add_new_range(self):
        """
        Add new ranges to the Default MAC pool
        """
        testflow.step("Add new ranges to the Default MAC pool")
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=mac_pool_conf.DEFAULT_MAC_POOL,
            range_list=mac_pool_conf.MAC_POOL_RANGE_LIST
        )

    @polarion("RHEVM3-14511")
    def test_02_remove_new_added_range(self):
        """
        Remove added ranges from the Default MAC pool
        """
        testflow.step("Remove added ranges from the Default MAC pool")
        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=mac_pool_conf.DEFAULT_MAC_POOL,
            range_list=mac_pool_conf.MAC_POOL_RANGE_LIST
        )


@pytest.mark.usefixtures(case_08_fixture.__name__)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestSanity08(TestSanityCaseBase):
    """
    Create new DC and cluster with non default management network
    Prepare networks on new DC
    Create new DC and cluster with default management network
    """
    __test__ = True
    net = "sanity_mgmt_net"
    nets = [net]
    dc = "sanity_extra_dc_0"
    cluster_1 = "sanity_extra_cluster_1"
    cluster_2 = "sanity_extra_cluster_2"
    mgmt_bridge = conf.MGMT_BRIDGE

    @polarion("RHEVM3-14512")
    def test_create_dc_cluster_with_management_net(self):
        """
        Create new DC and cluster with non default management network
        """
        testflow.step(
            "Create %s with %s as management network", self.cluster_1, self.net
        )
        assert mgmt_net_helper.add_cluster(
            cl=self.cluster_1, dc=self.dc, management_network=self.net
        )
        assert hl_networks.is_management_network(
            cluster_name=self.cluster_1, network=self.net
        )

    @polarion("RHEVM3-14513")
    def test_create_dc_cluster_with_default_management_net(self):
        """
        Create new DC and cluster with default management network
        """
        testflow.step(
            "Create new DC and cluster with default management network"
        )
        assert mgmt_net_helper.add_cluster(
            cl=self.cluster_2, dc=self.dc, management_network=self.mgmt_bridge
        )
        assert hl_networks.is_management_network(
            cluster_name=self.cluster_2, network=self.mgmt_bridge
        )


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__,
    attach_networks.__name__
)
@pytest.mark.incremental
class TestSanity09(TestSanityCaseBase):
    """
    Attach VM non-VLAN network with MTU 9000 to host NIC
    Change the network MTU
    Change the network to be tagged
    Change the network to be non-VM network
    """
    __test__ = True
    net = sanity_conf.NETS[9][0]
    nets = [net]
    dc = conf.DC_0
    nic = 1
    ip = None
    ip_addr_dict = None
    bond = None

    @polarion("RHEVM3-14515")
    def test_01_change_mtu(self):
        """
        Change the network MTU
        """
        mtu = conf.MTU[-1]
        mtu_dict = {
            "mtu": mtu
        }
        network_helper.call_function_and_wait_for_sn(
            func=ll_networks.update_network, content=self.net, positive=True,
            network=self.net, mtu=mtu
        )
        testflow.step(
            "Change the network MTU and check if the host is updated with "
            "the change"
        )
        assert hl_networks.check_host_nic_params(
            host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1], **mtu_dict
        )
        testflow.step(
            "Checking logical layer of bridged network %s on host %s",
            self.net, conf.HOST_0_NAME
        )
        assert test_utils.check_mtu(
            vds_resource=conf.VDS_0_HOST, mtu=mtu, physical_layer=False,
            network=self.net, nic=conf.HOST_0_NICS[1]
        ), "Logical layer: %s MTU should be %s" % (self.net, mtu)

        testflow.step(
            "Checking physical layer of bridged network %s on host %s",
            self.net, conf.HOST_0_NAME
        )
        assert test_utils.check_mtu(
            vds_resource=conf.VDS_0_HOST, mtu=mtu, nic=conf.HOST_0_NICS[1]
        ), "Physical layer: %s MTU should be %s" % (conf.HOST_0_NICS[1], mtu)

    @polarion("RHEVM3-14516")
    def test_02_change_vlan(self):
        """
        Change the network VLAN
        """
        vlan_id = sanity_conf.VLAN_IDS[11]
        vlan_dict = {"vlan_id": vlan_id}

        network_helper.call_function_and_wait_for_sn(
            func=ll_networks.update_network, content=self.net, positive=True,
            network=self.net, vlan_id=vlan_id
        )
        testflow.step(
            "Change the network VLAN and check if the Host is updated with "
            "the change"
        )
        assert hl_networks.check_host_nic_params(
            host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1], **vlan_dict
        )
        testflow.step("Check that the change is reflected to Host")
        assert ll_networks.is_vlan_on_host_network(
            vds_resource=conf.VDS_0_HOST, interface=conf.HOST_0_NICS[1],
            vlan=vlan_id
        ), "%s on host %s was not updated with correct VLAN %s" % (
            self.net, conf.HOST_0_NAME, vlan_id
        )

    @polarion("RHEVM3-14517")
    def test_03_change_to_non_vm(self):
        """
        Change the network to be non-VM network
        """
        bridge_dict = {"bridge": False}
        network_helper.call_function_and_wait_for_sn(
            func=ll_networks.update_network, content=self.net, positive=True,
            network=self.net, usages=""
        )
        testflow.step(
            "Change the network to be non-VM network and check if the Host is "
            "updated with the change"
        )
        assert hl_networks.check_host_nic_params(
            host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1], **bridge_dict
        )
        testflow.step("Check that the change is reflected to Host")
        assert not ll_networks.is_host_network_is_vm(
            vds_resource=conf.VDS_0_HOST, net_name=self.net
        ), "%s on host %s was not updated to be non-VM network" % (
            self.net, conf.HOST_0_NAME
        )


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__,
    attach_networks.__name__
)
class TestSanity10(TestSanityCaseBase):
    """
    Verify you can configure additional network beside management with gateway
    Verify you can remove network configured with gateway
    """
    __test__ = True
    gateway = multiple_gw_conf.GATEWAY
    netmask = conf.NETMASK
    subnet = multiple_gw_conf.SUBNET
    net = sanity_conf.NETS[10][0]
    nets = [net]
    nic = 1
    bond = None
    ip = network_helper.create_random_ips(num_of_ips=1, mask=24)[0]
    ip_addr_dict = {
        "ip_gateway": {
            "address": ip,
            "netmask": netmask,
            "boot_protocol": "static",
            "gateway": gateway
        }
    }

    @polarion("RHEVM3-3949")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        testflow.step("Check correct configuration with ip rule function")
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=self.subnet
        ), "Incorrect gateway configuration for %s" % self.net

    @polarion("RHEVM3-3965")
    def test_detach_gw_net(self):
        """
        Remove network with gw configuration from setup
        """
        sn_dict = {
            "remove": {
                "networks": [self.net]
            }
        }
        testflow.step("Remove network with gw configuration from setup")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(
    update_vnic_profile.__name__,
    start_vm.__name__
)
class TestSanity11(TestSanityCaseBase):
    """
    Configure queue on existing network
    """
    __test__ = True
    vm = conf.VM_0
    num_queues = multiple_queue_conf.NUM_QUEUES[0]
    prop_queue = multiple_queue_conf.PROP_QUEUES[0]
    dc = conf.DC_0
    mgmt_bridge = conf.MGMT_BRIDGE

    @polarion("RHEVM3-4309")
    def test_multiple_queue_nics(self):
        """
        Check that queue exists in qemu process
        """
        testflow.step("Check that queue exists in qemu process")
        assert network_helper.check_queues_from_qemu(
            vm=self.vm, host_obj=conf.VDS_0_HOST, num_queues=self.num_queues
        )


@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_networks.__name__
)
class TestSanity12(TestSanityCaseBase):
    """
    Attach network with bridge_opts and ethtool_opts to host NIC
    """
    __test__ = True
    net = sanity_conf.NETS[12][0]

    @polarion("RHEVM3-10478")
    def test_network_custom_properties_on_host(self):
        """
        Attach network with bridge_opts and ethtool_opts to host NIC
        """
        properties_dict = {
            "bridge_opts": custom_pr_conf.PRIORITY,
            "ethtool_opts": custom_pr_conf.TX_CHECKSUM.format(
                nic=conf.HOST_0_NICS[1], state="off"
            )
        }
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_0_NICS[1],
                    "properties": properties_dict
                }
            }
        }
        testflow.step(
            "Attach network with bridge_opts and ethtool_opts to host NIC"
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(
    start_vm.__name__
)
class TestSanity13(TestSanityCaseBase):
    """
    Check that Network Filter is enabled by default
    """
    __test__ = True
    vm = conf.VM_0
    mgmt_profile = conf.MGMT_BRIDGE

    @polarion("RHEVM3-3775")
    def test_check_filter_status_engine(self):
        """
        Check that Network Filter is enabled by default on engine
        """
        testflow.step(
            "Check that network filter (vdsm-no-mac-spoofing) is enabled by "
            "default for new network"
        )
        nf_attr_dict = ll_networks.get_vnic_profile_attr(
            name=self.mgmt_profile, network=self.mgmt_profile,
            attr_list=[nf_conf.NETWORK_FILTER_STR], data_center=conf.DC_0
        )
        nf_res = nf_attr_dict[nf_conf.NETWORK_FILTER_STR]
        assert nf_res == conf.VDSM_NO_MAC_SPOOFING

    @polarion("RHEVM3-3777")
    def test_check_filter_status_vdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        testflow.step(
            "Check that Network Filter is enabled by default on VDSM"
        )
        assert ll_hosts.check_network_filtering(
            positive=True, vds_resource=conf.VDS_0_HOST
        )

    @polarion("RHEVM3-3779")
    def test_check_filter_status_dump_xml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        testflow.step(
            "Check that Network Filter is enabled by default via dumpxml"
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm,
            nics="1"
        )


@pytest.mark.usefixtures(
    create_networks.__name__,
    attach_networks.__name__,
    add_labels.__name__
)
class TestSanity14(TestSanityCaseBase):
    """
    Attach VLAN and VM networks to NIC and BOND via labels
    """
    __test__ = True
    net_1_nic = sanity_conf.NETS[14][0]
    net_2_nic_vlan = sanity_conf.NETS[14][1]
    net_3_bond = sanity_conf.NETS[14][2]
    net_4_bond_vlan = sanity_conf.NETS[14][3]
    lb_1 = conf.LABEL_LIST[0]
    lb_2 = conf.LABEL_LIST[1]
    bond = "bond14"
    nic = bond
    nets = list()
    ip_addr_dict = None
    labels = {
        lb_1: [net_1_nic, net_2_nic_vlan],
        lb_2: [net_3_bond, net_4_bond_vlan]
    }

    @polarion("RHEVM3-13511")
    def test_label_nic_vm_vlan(self):
        """
        Check that untagged VM and VLAN networks are attached to the Host NIC
        via labels
        """
        testflow.step(
            "Check that untagged VM and VLAN networks are attached to the "
            "Host NIC via labels"
        )
        label_dict = {
            self.lb_1: {
                "host": conf.HOST_0_NAME,
                "nic": conf.HOST_0_NICS[1],
            }
        }
        assert ll_networks.add_label(**label_dict)
        for net in (self.net_1_nic, self.net_2_nic_vlan):
            assert hl_host_network.check_network_on_nic(
                network=net, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
            )

    @polarion("RHEVM3-13894")
    def test_label_bond_vm_vlan(self):
        """
        Check that the untagged VM and VLAN networks are attached to BOND via
        labels
        """
        testflow.step(
            "Check that the untagged VM and VLAN networks are attached to "
            "BOND via labels"
        )
        label_dict = {
            self.lb_2: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond,
            }
        }
        assert ll_networks.add_label(**label_dict)
        for net in (self.net_3_bond, self.net_4_bond_vlan):
            assert hl_host_network.check_network_on_nic(
                network=net, host=conf.HOST_0_NAME, nic=self.bond
            )


@pytest.mark.usefixtures(
    create_networks.__name__,
    deactivate_hosts.__name__,
    attach_networks.__name__,
    set_host_nic_down.__name__
)
class TestSanity15(TestSanityCaseBase):
    """
    Set network as required
    Set the network host NIC down
    Check that host status is non-operational
    """
    __test__ = True
    net = sanity_conf.NETS[15][0]
    nets = [net]
    ip_addr_dict = None
    nic = 1

    @bz({"1310417": {}})
    @polarion("RHEVM3-3750")
    def test_non_operational(self):
        """
        Check that Host is non-operational
        """
        testflow.step("Check that Host is non-operational")
        assert ll_hosts.waitForHostsStates(
            positive=True, names=conf.HOST_0_NAME, states="non_operational",
            timeout=conf.TIMEOUT * 2
        )
