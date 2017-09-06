#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Jumbo frames feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
jumbo frames will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as jumbo_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import (
    add_vnics_to_vms,
    restore_hosts_mtu,
    configure_mtu_on_host,
    prepare_setup_jumbo_frame
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    setup_networks_fixture,
    update_cluster_network_usages,
    clean_host_interfaces,
    remove_all_networks,
    create_and_attach_networks,
    remove_vnics_from_vms
)


@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_JUMBO_FRAME_SUPPORT, reason=conf.NO_JUMBO_FRAME_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(prepare_setup_jumbo_frame.__name__)
class TestJumboFramesTestCaseBase(NetworkTest):
    """
    Base class
    """
    pass


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestJumboFramesCase01(TestJumboFramesTestCaseBase):
    """
    Test VM network with MTU 5000
    """
    net = jumbo_conf.NETS[1][0]
    mtu_5000 = conf.MTU[1]
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_1_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3718")
    def test_check_mtu(self):
        """
        Check physical and logical levels for network with Jumbo frames
        """
        testflow.step(
            "Check physical and logical levels for network with Jumbo frames"
        )
        assert helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net, mtu=self.mtu_5000
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestJumboFramesCase02(TestJumboFramesTestCaseBase):
    """
    Attach two non-VM VLAN networks with Jumbo Frames
    Removes one of the networks
    Check the correct values for the MTU in files
    """
    net_1 = jumbo_conf.NETS[2][0]
    net_2 = jumbo_conf.NETS[2][1]
    vlan_1 = jumbo_conf.CASE_2_NETS.get(net_1).get("vlan_id")
    vlan_2 = jumbo_conf.CASE_2_NETS.get(net_2).get("vlan_id")
    mtu_5000 = conf.MTU[1]
    mtu_9000 = conf.MTU[0]
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_2_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 1,
                "network": net_2
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3721")
    def test_check_mtu_after_network_removal(self):
        """
        Remove one network from host
        Check physical and logical levels for networks with Jumbo frames
        """
        testflow.step("Remove one network from host")
        assert hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_2]
        )
        testflow.step(
            "Check physical and logical levels for networks with Jumbo frames"
        )
        assert helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_1, mtu=self.mtu_5000,
            vlan=self.vlan_1, bridge=False
        )


@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__,
    remove_vnics_from_vms.__name__
)
class TestJumboFramesCase03(TestJumboFramesTestCaseBase):
    """
    Check connectivity between two hosts
    Change BOND mode
    Add slave to BOND
    Check connectivity between two VMs
    """
    net = jumbo_conf.NETS[3][0]
    mtu_5000 = conf.MTU[1]
    mtu_4500 = str(conf.SEND_MTU[0])
    bond = "bond3"
    vm = conf.VM_0
    vms_ips = network_helper.create_random_ips(mask=24)
    hosts_ips = network_helper.create_random_ips(mask=24, base_ip_prefix="6")
    vnic = jumbo_conf.VNICS[3][0]
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_3_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        conf.VM_0: {
            "1": {
                "name": vnic
            }
        },
        conf.VM_1: {
            "1": {
                "name": vnic
            },
        }
    }

    # add_vnics_to_vms params
    vnic_1_params = {
        "mtu": mtu_5000,
        "network": net,
        "nic_name": vnic,
        "set_ip": True
    }
    vnics_to_add = [vnic_1_params]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": bond,
                "network": net,
                "slaves": [2, 3],
                "mode": 1,
                "ip": {
                    "1": {
                        "address": hosts_ips[0]
                    }
                }
            }
        },
        1: {
            net: {
                "nic": bond,
                "network": net,
                "slaves": [2, 3],
                "mode": 1,
                "ip": {
                    "1": {
                        "address": hosts_ips[1]
                    }
                }
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3732")
    def test_01_check_configurations_and_traffic(self):
        """
        Pass traffic between the hosts with configured MTU.
        """
        testflow.step("Pass traffic between the hosts with configured MTU.")
        assert network_helper.send_icmp_sampler(
            host_resource=conf.VDS_0_HOST, dst=self.hosts_ips[1],
            size=self.mtu_4500
        )

    @tier2
    @polarion("RHEVM3-3713")
    def test_02_bond_mode_change(self):
        """
        Change BOND mode
        Check physical and logical levels for networks with Jumbo frames
        """
        network_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "mode": 4,
                },
            }
        }
        testflow.step("Change BOND mode")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        )
        testflow.step(
            "Check physical and logical levels for networks with Jumbo frames"
        )
        assert helper.check_logical_physical_layer(
            network=self.net, mtu=self.mtu_5000, bond=self.bond,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3]
        )

    @tier2
    @polarion("RHEVM3-3716")
    def test_03_increasing_bond_nics(self):
        """
        Add slave to BOND
        Check physical and logical levels for networks with Jumbo frames
        """
        network_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "slaves": [conf.HOST_0_NICS[1]]
                }
            }
        }
        testflow.step("Add slave to BOND")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        )
        testflow.step(
            "Check physical and logical levels for networks with Jumbo frames"
        )
        assert helper.check_logical_physical_layer(
            bond=self.bond, network=self.net, mtu=self.mtu_5000,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3]
        )

    @tier2
    @polarion("RHEVM3-3722")
    def test_04_check_traffic_on_vm_over_bond(self):
        """
        Send ping with MTU 4500 between the two VMS
        """
        vm_resource = jumbo_conf.VMS_RESOURCES.get(self.vm)
        testflow.step("Send ping with MTU 4500 between the two VMS")
        assert network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.vms_ips[1],
            size=self.mtu_4500
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__,
    remove_vnics_from_vms.__name__
)
class TestJumboFramesCase04(TestJumboFramesTestCaseBase):
    """
    Attach 4 VLAN networks over BOND to two hosts
    Check that MTU is configured on the hosts
    Check connectivity between the hosts
    """
    bond = "bond4"
    net_1 = jumbo_conf.NETS[4][0]
    net_2 = jumbo_conf.NETS[4][1]
    net_3 = jumbo_conf.NETS[4][2]
    net_4 = jumbo_conf.NETS[4][3]
    vnic_1 = jumbo_conf.VNICS[4][0]
    vnic_2 = jumbo_conf.VNICS[4][1]
    mtu_8500 = str(conf.SEND_MTU[1])
    mtu_9000 = conf.MTU[0]
    mtu_5000 = str(conf.MTU[1])
    vm = conf.VM_0
    hosts_ips = network_helper.create_random_ips(mask=24, base_ip_prefix="6")
    vms_ips = network_helper.create_random_ips(mask=24)
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_4_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        conf.VM_0: {
            "1": {
                "name": vnic_1
            },
            "2": {
                "name": vnic_2
            }
        },
        conf.VM_1: {
            "1": {
                "name": vnic_1
            },
            "2": {
                "name": vnic_2
            }
        },
    }

    # add_vnics_to_vms params
    vnic_1_params = {
        "mtu": mtu_9000,
        "network": net_2,
        "nic_name": vnic_2,
        "set_ip": True
    }
    vnic_2_params = {
        "mtu": mtu_5000,
        "network": net_1,
        "nic_name": vnic_1,
        "set_ip": False
    }
    vnics_to_add = [vnic_1_params, vnic_2_params]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3],
                "mode": 4,
            },
            net_2: {
                "nic": bond,
                "network": net_2,
                "ip": {
                    "1": {
                        "address": hosts_ips[0]
                    }
                }
            },
            net_3: {
                "nic": bond
            },
            net_4: {
                "nic": bond
            }
        },
        1: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3],
                "mode": 4,
            },
            net_2: {
                "nic": bond,
                "network": net_2,
                "ip": {
                    "1": {
                        "address": hosts_ips[1]
                    }
                }
            },
            net_3: {
                "nic": bond
            },
            net_4: {
                "nic": bond
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3736")
    def test_check_traffic_on_hosts_when_there_are_many_networks(self):
        """
        Check that MTU is configured on the hosts
        Check connectivity between the hosts
        """
        list_check_networks = [
            conf.HOST_0_NICS[2], conf.HOST_0_NICS[3], self.bond
        ]
        testflow.step("Check that MTU is configured on the hosts")
        for element in list_check_networks:
            assert network_helper.check_configured_mtu(
                vds_resource=conf.VDS_0_HOST, mtu=str(self.mtu_9000),
                inter_or_net=element
            )
        assert helper.check_logical_physical_layer(
            mtu=self.mtu_9000, bond=self.bond,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3],
            logical=False
        )
        testflow.step("Check connectivity between the hosts")
        assert network_helper.send_icmp_sampler(
            host_resource=conf.VDS_0_HOST, dst=self.hosts_ips[1],
            size=self.mtu_8500
        )

    @tier2
    @polarion("RHEVM3-3731")
    def test_check_traffic_on_vms_when_host_has_many_networks(self):
        """
        Send ping with MTU 8500 between the two VMs
        """
        testflow.step("Send ping with MTU 8500 between the two VMs")
        vm_resource = jumbo_conf.VMS_RESOURCES.get(self.vm)
        assert network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.vms_ips[1],
            size=self.mtu_8500
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    update_cluster_network_usages.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__,
    remove_vnics_from_vms.__name__
)
class TestJumboFramesCase05(TestJumboFramesTestCaseBase):
    """
    Creates bridged VLAN network with 5000 MTU values
    and as display, Attaching the network to VMs and checking the traffic
    between them
    """
    net = jumbo_conf.NETS[5][0]
    mtu_5000 = str(conf.MTU[1])
    mtu_4500 = str(conf.SEND_MTU[0])
    vnic = jumbo_conf.VNICS[5][0]
    hosts_ips = network_helper.create_random_ips(mask=24, base_ip_prefix="6")
    vms_ips = network_helper.create_random_ips(mask=24)
    vm = conf.VM_0
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_5_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        conf.VM_0: {
            "1": {
                "name": vnic
            }
        },
        conf.VM_1: {
            "1": {
                "name": vnic
            },
        }
    }

    # add_vnics_to_vms params
    vnic_1_params = {
        "mtu": mtu_5000,
        "network": net,
        "nic_name": vnic,
        "set_ip": True
    }
    vnics_to_add = [vnic_1_params]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net,
                "ip": {
                    "1": {
                        "address": hosts_ips[0]
                    }
                }
            }
        },
        1: {
            net: {
                "nic": 1,
                "network": net,
                "ip": {
                    "1": {
                        "address": hosts_ips[1]
                    }
                }
            }
        }
    }

    # restore_network_usage params
    network_usage = conf.MGMT_BRIDGE
    cluster_usage = conf.CL_0

    # update_cluster_network_usages params
    update_cluster = conf.CL_0
    update_cluster_network = net
    update_cluster_network_usages = "display,vm"

    @tier2
    @polarion("RHEVM3-3724")
    def test_check_traffic_on_vm_when_network_is_display(self):
        """
        Send ping between 2 VMS
        """
        vm_resource = jumbo_conf.VMS_RESOURCES.get(self.vm)
        testflow.step("Send ping with size 4500 between 2 VMS")
        assert network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.vms_ips[1],
            size=self.mtu_4500
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    restore_hosts_mtu.__name__
)
class TestJumboFramesCase06(TestJumboFramesTestCaseBase):
    """
    Try to attach VM VLAN network and non-VM network with different MTU to the
    same BOND
    """
    net_1 = jumbo_conf.NETS[6][0]
    net_2 = jumbo_conf.NETS[6][1]
    bond = "bond6"
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_6_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier2
    @polarion("RHEVM3-3719")
    def test_neg_add_networks_with_different_mtu(self):
        """
        Try to attach VM VLAN network and non-VM network with different MTU to
        the same BOND
        """
        network_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": self.bond,
                    "slaves": conf.HOST_0_NICS[2:4]
                },
                "2": {
                    "network": self.net_2,
                    "nic": self.bond
                }
            }
        }
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__,
    remove_vnics_from_vms.__name__
)
class TestJumboFramesCase07(TestJumboFramesTestCaseBase):
    """
    Creates 2 bridged VLAN networks with different MTU and check traffic
    Check physical and logical levels for bridged VLAN networks
    between VMs over those networks
    """
    net_1 = jumbo_conf.NETS[7][0]
    net_2 = jumbo_conf.NETS[7][1]
    vlan_1 = conf.REAL_VLANS[0] if conf.REAL_VLANS else None
    vlan_2 = conf.REAL_VLANS[1] if conf.REAL_VLANS else None
    mtu_5000 = conf.MTU[1]
    mtu_9000 = conf.MTU[0]
    mtu_4500 = str(conf.SEND_MTU[0])
    vnic = jumbo_conf.VNICS[7][0]
    vm_0 = conf.VM_0
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_7_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        conf.VM_0: {
            "1": {
                "name": vnic
            }
        },
        conf.VM_1: {
            "1": {
                "name": vnic
            },
        }
    }
    vms_ips = network_helper.create_random_ips(mask=24)

    # add_vnics_to_vms params
    vnic_1_params = {
        "mtu": mtu_5000,
        "network": net_1,
        "nic_name": vnic,
        "set_ip": True
    }
    vnics_to_add = [vnic_1_params]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
            },
            net_2: {
                "nic": 1,
                "network": net_2,
            }
        },
        1: {
            net_1: {
                "nic": 1,
                "network": net_1,
            },
            net_2: {
                "nic": 1,
                "network": net_2,
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3717")
    def test_check_mtu_values_in_files(self):
        """
        Check physical and logical levels for bridged VLAN networks
        """
        testflow.step(
            "Check physical and logical levels for bridged VLAN networks"
        )
        assert helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_1, mtu=self.mtu_5000,
            vlan=self.vlan_1, physical=False
        )
        assert helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_2, mtu=self.mtu_9000,
            vlan=self.vlan_2
        )

    @tier2
    @polarion("RHEVM3-3720")
    def test_check_traffic_on_vms(self):
        """
        Send ping between 2 VMs
        """
        vm_resource = jumbo_conf.VMS_RESOURCES.get(self.vm_0)
        testflow.step("Send ping between 2 VMs")
        assert network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.vms_ips[1],
            size=self.mtu_4500
        )
        for host_name in conf.HOST_0_NAME, conf.HOST_1_NAME:
            assert hl_host_network.remove_networks_from_host(
                host_name=host_name, networks=[self.net_2]
            )
        assert network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.vms_ips[1],
            size=self.mtu_4500
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestJumboFramesCase08(TestJumboFramesTestCaseBase):
    """
    Attach bridged VLAN network over BOND on Host with MTU 5000
    Add another network with MTU 1500 to the BOND
    Check that MTU on NICs are configured correctly on the logical and
    physical layers.
    """
    net_1 = jumbo_conf.NETS[8][0]
    net_2 = jumbo_conf.NETS[8][1]
    vlan_1 = jumbo_conf.CASE_8_NETS.get(net_1).get("vlan_id")
    vlan_2 = jumbo_conf.CASE_8_NETS.get(net_2).get("vlan_id")
    mtu_5000 = conf.MTU[1]
    mtu_1500 = conf.MTU[3]
    bond = "bond8"
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_8_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3]
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3716")
    def test_check_mtu_with_two_different_mtu_networks(self):
        """
        Add another network with MTU 1500 to the BOND
        Check physical and logical levels for networks with Jumbo frames
        """
        network_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": self.bond,
                }
            }
        }
        testflow.step("Add another network with MTU 1500 to the BOND")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        )
        testflow.step(
            "Check physical and logical levels for networks with Jumbo frames"
        )
        assert helper.check_logical_physical_layer(
            bond=self.bond, network=self.net_1, mtu=self.mtu_5000,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3]
        )
        assert helper.check_logical_physical_layer(
            bond=self.bond, network=self.net_2, mtu=self.mtu_1500,
            physical=False
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    configure_mtu_on_host.__name__,
    setup_networks_fixture.__name__
)
class TestJumboFramesCase09(TestJumboFramesTestCaseBase):
    """
    Configure MTU 2000 on host NIC (via ssh)
    Attach network to the same host NIC without MTU
    Check that host NIC MTU is changed to 1500
    """
    mtu_1500 = str(conf.MTU[3])
    mtu = str(conf.MTU[2])
    net = jumbo_conf.NETS[9][0]
    host_nic_index = 1
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "networks": jumbo_conf.CASE_9_NETS,
            "data_center": dc,
            "clusters": [conf.CL_0],
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net,
            }
        }
    }

    @tier2
    @polarion("RHEVM3-3734")
    def test_check_mtu_pre_configured(self):
        """
        Check that host NIC MTU is changed to 1500
        """
        testflow.step("Check that host NIC MTU is changed to 1500")
        assert network_helper.check_configured_mtu(
            vds_resource=conf.VDS_0_HOST, mtu=self.mtu_1500,
            inter_or_net=conf.HOST_0_NICS[1]
        )
