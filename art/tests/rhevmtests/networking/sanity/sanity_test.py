#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Sanity for the network features.
"""

import config as sanity_conf

import pytest
from fixtures import (
    add_labels,
    add_network_to_dc,
    add_vnic_profile,
    create_cluster,
    create_vnics_on_vm,
    nmcli_create_networks,
    prepare_setup_for_register_domain,
    remove_qos,
    update_vnic_profile
)
from rhevmtests.networking.mac_pool_range_per_cluster import (
    config as mac_pool_conf,
    helper as mac_pool_helper
)
from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    mac_pool as hl_mac_pool,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    hosts as ll_hosts,
    mac_pool as ll_mac_pool,
    networks as ll_networks,
    vms as ll_vms
)
import rhevmtests.helpers as global_helper
import rhevmtests.networking.active_bond_slave.helper as active_bond_helper
from rhevmtests.networking import config as conf, helper as network_helper
import rhevmtests.networking.multi_host.helper as multi_host_helper
import rhevmtests.networking.multiple_gateways.config as multiple_gw_conf
import rhevmtests.networking.multiple_queue_nics.config as multiple_queue_conf
import rhevmtests.networking.network_custom_properties.config as custom_pr_conf
import rhevmtests.networking.network_filter.config as nf_conf
import rhevmtests.networking.register_domain.helper as register_helper
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    NetworkTest,
    tier1,
    testflow,
)
from rhevmtests.fixtures import create_clusters, create_datacenters, start_vm
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    create_and_attach_networks,
    remove_all_networks,
    update_vnic_profiles
)
from rhevmtests.networking.register_domain.fixtures import (
    import_vm_from_data_domain
)
from rhevmtests.networking.sr_iov.fixtures import (  # noqa: F401
    add_vnics_to_vm,
    reset_host_sriov_params,
    set_num_of_vfs,
    sr_iov_init
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    add_vnic_profile.__name__
)
class TestSanity01(NetworkTest):
    """
    Create new vNIC profile and make sure all its parameters exist in API
    """
    # update_vnic_profiles params
    net = sanity_conf.NETS[1][0]
    dc = conf.DC_0
    vnic_profile = sanity_conf.VNIC_PROFILES[1][0]
    description = "sanity_vnic_profile_test"

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
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


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__
)
class TestSanity02(NetworkTest):
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
    # General params
    dc = conf.DC_0
    net = sanity_conf.NETS[2]
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    bond_4 = "bond24"

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_2_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
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

    @tier1
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
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__,
    remove_qos.__name__,
)
class TestSanity03(NetworkTest):
    """
    Add new network QOS (named)
    Attach network with QoS to host NIC
    """
    # General params
    dc = conf.DC_0
    net = sanity_conf.NETS[3][0]

    # remove_qos params
    qos_name = sanity_conf.QOS_NAME[3][0]

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_3_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @polarion("RHEVM3-6525")
    def test_add_network_qos(self):
        """
        Create new Host Network QoS profile under DC
        """
        testflow.step("Create new Host Network QoS profile under DC")
        assert ll_dc.add_qos_to_datacenter(
            datacenter=conf.DC_0, qos_name=self.qos_name,
            qos_type=conf.HOST_NET_QOS_TYPE,
            outbound_average_linkshare=conf.QOS_TEST_VALUE
        )

    @tier1
    @polarion("RHEVM3-6526")
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
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestSanity04(NetworkTest):
    """
    Test MTU over VM/Non-VM/VLAN and BOND
    """
    # General
    mtu_bond = "bond40"
    non_vm_bond_1 = "bond41"
    non_vm_bond_2 = "bond42"
    dc = conf.DC_0

    # MTU cases
    # MTU over VM network params
    mtu_vm_net_params = [sanity_conf.NETS[4][0], 1]

    # MTU over Non-VM network params
    mtu_non_vm_net_params = [sanity_conf.NETS[4][1], 2]

    # MTU over VLAN VM network params
    mtu_vlan_vm_net_params = [sanity_conf.NETS[4][2], 3]

    # MTU over BOND VM network params
    mtu_bond_vm_net_params = [sanity_conf.NETS[4][3], mtu_bond]

    # Non-VM cases
    # Non-VM network params
    non_vm_net_params = [sanity_conf.NETS[4][4], 10]

    # Non-VM VLAN network params
    non_vm_vlan_net_params = [sanity_conf.NETS[4][5], 11]

    # Non-VM BOND network params
    non_vm_bond_net_params = [sanity_conf.NETS[4][6], non_vm_bond_1]

    # Non-VM VLAN BOND network params
    non_vm_vlan_bond_net_params = [sanity_conf.NETS[4][7], non_vm_bond_2]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            mtu_bond: {
                "nic": mtu_bond,
                "slaves": [4, 5]
            },
            non_vm_bond_1: {
                "nic": non_vm_bond_1,
                "slaves": [6, 7]
            },
            non_vm_bond_2: {
                "nic": non_vm_bond_2,
                "slaves": [8, 9]
            },
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_4_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @pytest.mark.parametrize(
        ("network", "nic"),
        [
            # MTU cases
            pytest.param(*mtu_vm_net_params, marks=(polarion("RHEVM3-14499"))),
            pytest.param(
                *mtu_non_vm_net_params, marks=(polarion("RHEVM3-14500"))
            ),
            pytest.param(
                *mtu_vlan_vm_net_params, marks=(polarion("RHEVM3-14501"))
            ),
            pytest.param(
                *mtu_bond_vm_net_params, marks=(polarion("RHEVM3-14502"))
            ),

            # Non-VM cases
            pytest.param(*non_vm_net_params, marks=(polarion("RHEVM3-14503"))),
            pytest.param(
                *non_vm_vlan_net_params, marks=(polarion("RHEVM3-14504"))
            ),
            pytest.param(
                *non_vm_bond_net_params, marks=(polarion("RHEVM3-14505"))
            ),
            pytest.param(
                *non_vm_vlan_bond_net_params, marks=(polarion("RHEVM3-14506"))
            ),
        ],
        ids=[
            # MTU cases
            "MTU_VM_network",
            "MTU_Non-VM_network",
            "MTU_VLAN",
            "MTU_BOND",

            # Non-VM cases
            "Non-VM_network",
            "Non-VM_VLAN",
            "Non-VM_BOND",
            "Non-VM_VLAN_BOND"
        ]
    )
    def test_attach_network(self, network, nic):
        """
        Attach networks with MTU to host
        """
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        sn_dict = {
            "add": {
                "1": {
                    "nic": host_nic,
                    "network": network
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    add_labels.__name__
)
class TestSanity05(NetworkTest):
    """
    Attach VLAN and VM networks to NIC and BOND via labels
    """
    # General params
    bond = "bond5"
    dc = conf.DC_0

    # Label on host NIC params
    host_nic_nets = sanity_conf.NETS[5][:2]
    lb_1 = conf.LABEL_LIST[0]
    host_nic_label_params = [host_nic_nets, lb_1, 1]

    # Label on BOND params
    host_bond_nets = sanity_conf.NETS[5][2:4]
    lb_2 = conf.LABEL_LIST[1]
    host_bond_label_params = [host_bond_nets, lb_2, bond]

    # add_labels params
    labels = {
        lb_1: host_nic_nets,
        lb_2: host_bond_nets
    }

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "slaves": [2, 3],
                "nic": bond,
            },
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_5_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @pytest.mark.parametrize(
        ("networks", "label", "nic"),
        [
            pytest.param(
                *host_nic_label_params, marks=(polarion("RHEVM3-13511"))
            ),
            pytest.param(
                *host_bond_label_params, marks=(polarion("RHEVM3-13894"))
            ),
        ],
        ids=[
            "On_host_NIC",
            "On_BOND"
        ]
    )
    def test_attach_label(self, networks, label, nic):
        """
        Attach VLAN and VM networks to NIC and BOND via labels
        """
        host = conf.HOST_0_NAME
        host_nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        testflow.step(
            "Check that untagged VM and VLAN networks are attached to the "
            "%s via label %s", host_nic, label
        )
        label_dict = {
            label: {
                "host": ll_hosts.get_host_object(host_name=host),
                "nic": host_nic,
            }
        }
        assert ll_networks.add_label(**label_dict)
        for net in networks:
            assert hl_host_network.check_network_on_nic(
                network=net, host=host, nic=host_nic
            )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    create_vnics_on_vm.__name__,
    start_vm.__name__
)
class TestSanity06(NetworkTest):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    # General params
    dc = conf.DC_0

    # create_vnics_on_vm params
    vnics = sanity_conf.VNICS[6]
    nets = sanity_conf.NETS[6][:4]
    vm_name = conf.VM_0
    net_1 = nets[0]
    net_2 = nets[1]
    net_3 = nets[2]
    net_4 = nets[3]

    # start_vm params
    start_vms_dict = {
        vm_name: {}
    }

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "network": net_1,
                "nic": 1,
            },
            net_2: {
                "network": net_2,
                "nic": 1,
            },
            net_3: {
                "network": net_3,
                "nic": 1,
            },
            net_4: {
                "network": net_4,
                "nic": 1,
            },
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_6_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @bz({"1478007": {}})
    @polarion("RHEVM3-3829")
    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        testflow.step(
            "Check all permutation for the Plugged/Linked options on VNIC"
        )
        for nic_name in (
            self.vnics[0], self.vnics[2], self.vnics[4]
        ):
            assert ll_vms.get_vm_nic_linked(vm=self.vm_name, nic=nic_name)

        for nic_name in (
            self.vnics[0], self.vnics[1], self.vnics[4]
        ):
            assert ll_vms.get_vm_nic_plugged(vm=self.vm_name, nic=nic_name)

        for nic_name in (self.vnics[1], self.vnics[3]):
            assert not ll_vms.get_vm_nic_linked(vm=self.vm_name, nic=nic_name)

        for nic_name in (self.vnics[2], self.vnics[3]):
            assert not ll_vms.get_vm_nic_plugged(vm=self.vm_name, nic=nic_name)


@pytest.mark.usefixtures(create_cluster.__name__)
class TestSanity07(NetworkTest):
    """
    1. Create a new cluster and check it was created with updated Default
    MAC pool values
    2. Extend the default range values of Default MAC pool
    3. Add new ranges to the Default MAC pool
    4. Remove added ranges from the Default MAC pool
    """
    # create_cluster params
    ext_cl = mac_pool_conf.EXT_CL_1

    @tier1
    @polarion("RHEVM3-14507")
    def test_check_default_mac_new_dc(self):
        """
        Check default MAC pool
        """
        testflow.step(
            "Check that the new DC was created with default MAC pool"
        )
        default_mac_id = ll_mac_pool.get_default_mac_pool().get_id()
        ext_cl_mac_id = ll_mac_pool.get_mac_pool_from_cluster(
            cluster=self.ext_cl
        ).get_id()
        assert default_mac_id == ext_cl_mac_id

    @tier1
    @polarion("RHEVM3-14509")
    def test_extend_default_mac_range(self):
        """
        Extend the default range values of Default MAC pool
        """
        testflow.step("Extend the default range values of Default MAC pool")
        assert mac_pool_helper.update_mac_pool_range_size(
            mac_pool_name=mac_pool_conf.DEFAULT_MAC_POOL, size=(2, 2)
        )

    @tier1
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

    @tier1
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


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    create_datacenters.__name__,
    create_clusters.__name__,
    add_network_to_dc.__name__
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestSanity08(NetworkTest):
    """
    Create new DC and cluster with non default management network
    Prepare networks on new DC
    Create new DC and cluster with default management network
    """
    # General params
    dc = "sanity_extra_dc_0"
    dc_for_nets = conf.DC_0

    # Datacenter with custom management network params
    custom_mgmt_net = "sanity_mgmt_net"
    custom_mgmt_cluster = "sanity_extra_cluster_1"
    custom_mgmt_net_params = [custom_mgmt_cluster, custom_mgmt_net]

    # Datacenter with default management network params
    mgmt_bridge = conf.MGMT_BRIDGE
    default_mgmt_cluster = "sanity_extra_cluster_2"
    default_mgmt_net_params = [default_mgmt_cluster, mgmt_bridge]

    # add_network_to_dc params
    net = custom_mgmt_net

    # create_clusters params
    clusters_to_remove = [custom_mgmt_cluster, default_mgmt_cluster]

    # create_datacenters params
    datacenters_dict = {
        dc: {
            "name": dc,
            "version": conf.COMP_VERSION,
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc_for_nets,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_8_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc_for_nets]

    @tier1
    @pytest.mark.parametrize(
        ("cluster", "network"),
        [
            pytest.param(
                *custom_mgmt_net_params, marks=(polarion("RHEVM3-14512"))
            ),
            pytest.param(
                *default_mgmt_net_params, marks=(polarion("RHEVM3-14513"))
            ),
        ],
        ids=[
            "With_custom_management_network",
            "With_default_management_network"
        ]
    )
    def test_create_dc_cluster(self, cluster, network):
        """
        Create new DC and cluster with non default management network
        Create new DC and cluster with default management network
        """
        testflow.step(
            "Create %s with %s as management network", cluster, network
        )
        assert ll_clusters.addCluster(
            positive=True, name=cluster, data_center=self.dc,
            cpu=conf.CPU_NAME, version=conf.COMP_VERSION,
            management_network=network
        )
        assert hl_networks.is_management_network(
            cluster_name=cluster, network=network
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestSanity09(NetworkTest):
    """
    Attach VM non-VLAN network with MTU 9000 to host NIC
    Change the network MTU
    Change the network to be tagged
    Change the network to be non-VM network
    """
    # General params
    dc = conf.DC_0

    # test params = [Network, update dict to check, host NIC, update type]
    # Update MTU params
    mtu_net = sanity_conf.NETS[9][0]
    mtu_dict = {"mtu": conf.MTU[-1]}
    mtu_params = [mtu_net, mtu_dict, 1]

    # Update VLAN params
    vlan_net = sanity_conf.NETS[9][1]
    vlan_dict = {"vlan_id": conf.DUMMY_VLANS.pop(0)}
    vlan_params = [vlan_net, vlan_dict, 2]

    # Update Non-VM params
    vm_net = sanity_conf.NETS[9][2]
    bridge_dict = {"bridge": False}
    bridge_params = [vm_net, bridge_dict, 3]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            mtu_net: {
                "network": mtu_net,
                "nic": 1,
            },
            vlan_net: {
                "network": vlan_net,
                "nic": 2,
            },
            vm_net: {
                "network": vm_net,
                "nic": 3,
            },
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_9_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @pytest.mark.parametrize(
        ("network", "update_params", "nic"),
        [
            pytest.param(
                *mtu_params, marks=(
                    (polarion("RHEVM3-14515")), bz({"1460687": {}}))
            ),
            pytest.param(*vlan_params, marks=(polarion("RHEVM3-14516"))),
            pytest.param(*bridge_params, marks=(polarion("RHEVM3-14517"))),
        ],
        ids=[
            "Update_network_MTU",
            "Update_network_VLAN_ID",
            "Update_network_to_Non-VM"
        ]
    )
    def test_update_networks(self, network, update_params, nic):
        """
        Change the network MTU
        Change the network to be tagged
        Change the network to be non-VM network
        """
        testflow.step("Update network %s with %s", network, update_params)
        assert multi_host_helper.update_network_and_check_changes(
            net=network, nic=nic, **update_params
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestSanity10(NetworkTest):
    """
    Verify you can configure additional network beside management with gateway
    Verify you can remove network configured with gateway
    """
    # General params
    dc = conf.DC_0
    gateway = multiple_gw_conf.GATEWAY
    netmask = conf.NETMASK
    subnet = multiple_gw_conf.SUBNET
    net = sanity_conf.NETS[10][0]
    ip = network_helper.create_random_ips(num_of_ips=1, mask=24)[0]
    ip_addr_dict = {
        "ip_gateway": {
            "address": ip,
            "netmask": netmask,
            "boot_protocol": "static",
            "gateway": gateway
        }
    }

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net: {
                "network": net,
                "nic": 1,
                "ip": ip_addr_dict
            },
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_10_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @polarion("RHEVM3-3949")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        testflow.step("Check correct configuration with ip rule function")
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=self.subnet
        ), "Incorrect gateway configuration for %s" % self.net

    @tier1
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
class TestSanity11(NetworkTest):
    """
    Configure queue on existing network
    """
    # General params
    vm_name = conf.VM_0
    num_queues = multiple_queue_conf.NUM_QUEUES[0]

    # update_vnic_profile params
    prop_queue = multiple_queue_conf.PROP_QUEUES[0]
    dc = conf.DC_0
    mgmt_bridge = conf.MGMT_BRIDGE

    # start_vm params
    start_vms_dict = {
        vm_name: {}
    }

    @tier1
    @bz({"1478054": {}})
    @polarion("RHEVM3-4309")
    def test_multiple_queue_nics(self):
        """
        Check that queue exists in qemu process
        """
        testflow.step("Check that queue exists in qemu process")
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__
)
class TestSanity12(NetworkTest):
    """
    Attach network with bridge_opts and ethtool_opts to host NIC
    """
    dc = conf.DC_0
    net = sanity_conf.NETS[12][0]

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_12_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
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


@pytest.mark.incremental
@pytest.mark.usefixtures(start_vm.__name__)
class TestSanity13(NetworkTest):
    """
    Check that Network Filter is enabled by default
    """
    # General params
    vm_name = conf.VM_0
    mgmt_profile = conf.MGMT_BRIDGE

    # start_vm param
    start_vms_dict = {
        vm_name: {}
    }

    @tier1
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
        nf_res = nf_attr_dict.get(nf_conf.NETWORK_FILTER_STR)
        assert nf_res == conf.VDSM_NO_MAC_SPOOFING

    @tier1
    @polarion("RHEVM3-3777")
    def test_check_filter_status_vdsm(self):
        """
        Check that Network Filter is enabled by default on VDSM
        """
        sanity_conf.HOST_NAME = ll_vms.get_vm_host(vm_name=self.vm_name)
        assert sanity_conf.HOST_NAME
        sanity_conf.HOST_VDS = global_helper.get_host_resource_by_name(
            host_name=sanity_conf.HOST_NAME
        )
        assert sanity_conf.HOST_VDS
        testflow.step(
            "Check that Network Filter is enabled by default on VDSM"
        )
        assert ll_hosts.check_network_filtering(
            positive=True, vds_resource=sanity_conf.HOST_VDS
        )

    @tier1
    @polarion("RHEVM3-3779")
    def test_check_filter_status_dump_xml(self):
        """
        Check that Network Filter is enabled by default via dumpxml
        """
        testflow.step(
            "Check that Network Filter is enabled by default via dumpxml"
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=sanity_conf.HOST_VDS, vm=self.vm_name,
            nics="1"
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__
)
class TestSanity14(NetworkTest):
    """
    Attach VM network with static IPv6 over bridge:
    """
    # General params
    dc = conf.DC_0
    net_1 = sanity_conf.NETS[14][0]
    ip_v6_1 = sanity_conf.IPV6_IPS.pop(0)

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_14_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @polarion("RHEVM-16627")
    def test_static_ipv6_network_on_host(self):
        """
        Attach network with static IPv6 over bridge.
        """
        conf.BASIC_IPV6_DICT["ip"]["address"] = self.ip_v6_1
        sn_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "ip": conf.BASIC_IPV6_DICT
                },
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )


@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestSanity15(NetworkTest):
    """
    1. Create bond with mode 1 - active-backup.
    2. Check that the engine report the correct active slave of the BOND.
    """
    # setup_networks_fixture params
    bond_1 = "bond01"
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [2, 3],
                "mode": 1
            },
        }
    }

    @tier1
    @polarion("RHEVM-17189")
    def test_report_active_slave(self,):
        """
        Verify that RHV is report primary/active interface of the bond mode 1.
        """
        testflow.step(
            "Check that the active slave name bond %s mode 1 that reported "
            "via engine match to the active slave name on the host",
            self.bond_1
        )
        assert active_bond_helper.compare_active_slave_from_host_to_engine(
            bond=self.bond_1
        ), (
            "Active slave name bond %s mode 1 that reported via engine "
            "isn't match to the active slave name on the host" % self.bond_1
        )


@bz({"1508908": {}})
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    prepare_setup_for_register_domain.__name__,
    import_vm_from_data_domain.__name__
)
class TestSanity16(NetworkTest):
    """
    Import VM from storage data domain when MAC is not from pool and network
    not is datacenter and reassessing MAC is checked and mapping the network
    in the import process
    """
    # General params
    dc = conf.DC_0
    dst_net = sanity_conf.NETS[16][1]

    # prepare_setup_for_register_domain params
    vm = sanity_conf.REGISTER_VM_NAME
    vm_nic = sanity_conf.REGISTER_VM_NIC
    net = sanity_conf.NETS[16][0]
    src_net = net

    # import_vm_from_data_domain params
    data_domain_name = sanity_conf.EXTRA_SD_NAME
    network_mappings = [{
        "source_network_profile_name": src_net,
        "source_network_name": src_net,
        "target_network": dst_net,
        "target_vnic_profile": dst_net
    }]

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_16_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @polarion("RHEVM-16998")
    def test_mac_pool_not_in_mac_range_with_reassign(self):
        """
        Check that MAC of imported VM is from the MAC pool
        """
        testflow.step(
            "Check the MAC of imported VM %s is from the MAC pool", self.vm
        )
        assert register_helper.check_mac_in_mac_range(
            vm=self.vm, nic=self.vm_nic
        )

    @tier1
    @polarion("RHEVM-17163")
    def test_network_not_in_dc_with_mapping(self):
        """
        Check that network of imported VM was mapped to new network
        """
        testflow.step(
            "Check the network %s of imported VM %s changed to %s",
            self.src_net, self.vm, self.dst_net
        )
        assert ll_vms.check_vnic_on_vm_nic(
            vm=self.vm, nic=self.vm_nic, vnic=self.dst_net
        )


@pytest.mark.usefixtures(
    sr_iov_init.__name__,
    create_and_attach_networks.__name__,
    reset_host_sriov_params.__name__,
    set_num_of_vfs.__name__,
    update_vnic_profiles.__name__,
    add_vnics_to_vm.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT,
    reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
class TestSanity17(NetworkTest):
    """
    Test start VM with passthrough vNIC profile.
    """

    # General
    vm = conf.VM_0
    vm_nic_1 = sanity_conf.VNIC_PROFILES[17][0]
    net_1 = sanity_conf.NETS[17][0]
    dc = conf.DC_0

    # remove_vnics_from_vm
    nics = [vm_nic_1]

    # set_num_of_vfs
    num_of_vfs = 1

    # update_vnic_profiles
    update_vnics_profiles = {
        net_1: {
            "pass_through": True,
            "network_filter": "None"
        }
    }

    # add_vnics_to_vm
    pass_through_vnic = [True]
    profiles = [net_1]
    vms = [vm]
    nets = profiles

    # start_vm
    vms_to_stop = vms

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_17_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @bz({"1479484": {}})
    @polarion("RHEVM-19654")
    def test_01_run_vm_with_passthrough_vnic_profile_and_one_vf(self):
        """
        Start VM when there are one VF with passthrough vNIC profile.
        """
        testflow.step(
            "Start VM: %s which uses passthrough vNIC profile", self.vm
        )
        assert ll_vms.startVm(positive=True, vm=self.vm)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces.__name__,
    nmcli_create_networks.__name__
)
class TestSanity18(NetworkTest):
    """
    Create flat connection via NetworkManager and use it via VDSM
    """
    # General params
    dc = conf.DC_0

    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # NetworkManager flat network params
    flat_connection = "flat_nm_net"
    flat_type = "nic"
    flat_rhv_network = sanity_conf.NETS[18][0]

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": sanity_conf.CASE_18_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier1
    @bz({"1426225": {}})
    @polarion("RHEVM-19392")
    def test_acquire_nm_connetion(self):
        """
        Use network that was created via NetworkManager in VDSM
        """
        sn_dict = {
            "add": {
                "1": {
                    "network": self.flat_rhv_network,
                    "nic": conf.HOST_0_NICS[1],
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
