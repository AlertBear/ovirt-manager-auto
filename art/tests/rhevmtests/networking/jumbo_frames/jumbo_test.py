#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Jumbo frames feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
jumbo frames will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import helper
import logging
import pytest
import config as conf
from rhevmtests import networking
from art.rhevm_api.utils import test_utils
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Jumbo_Frames_Cases")


def setup_module():
    """
    Start two VMs on separated hosts
    Get VMs IPs
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_1_NAME = conf.HOSTS[1]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.VDS_1_HOST = conf.VDS_HOSTS[1]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    conf.HOST_1_NICS = conf.VDS_1_HOST.nics
    vms_list = [conf.VM_0, conf.VM_1]
    hosts_list = [conf.HOST_0_NAME, conf.HOST_1_NAME]
    networking.network_cleanup()

    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )
    for vm, host in zip(vms_list, hosts_list):
        if not network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()


def teardown_module():
    """
    Set all hosts interfaces with MTU 1500
    Clean hosts interfaces
    Stop VMs
    Remove networks from engine
    """
    network_dict = {
        "1": {
            "network": "clear_net_1",
            "nic": None
        },
        "2": {
            "network": "clear_net_1",
            "nic": None
        },
        "3": {
            "network": "clear_net_1",
            "nic": None
        }
    }

    for host, nics in zip(
        [conf.HOST_0_NAME, conf.HOST_1_NAME],
        [conf.HOST_0_NICS, conf.HOST_1_NICS]
    ):
        network_dict["1"]["nic"] = nics[1]
        network_dict["2"]["nic"] = nics[2]
        network_dict["3"]["nic"] = nics[3]
        hl_host_network.setup_networks(host_name=host, **network_dict)
        hl_host_network.clean_host_interfaces(host_name=host)

    ll_vms.stopVms(vms=[conf.VM_0, conf.VM_1])
    hl_networks.remove_net_from_setup(
        host=conf.HOSTS[:2], data_center=conf.DC_0,
        mgmt_network=conf.MGMT_BRIDGE, all_net=True
    )


@attr(tier=2)
class TestJumboFramesTestCaseBase(NetworkTest):
    """
    Base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup and update MTU to be default on all
        Hosts NICs
        """
        helper.restore_mtu_and_clean_interfaces()


class TestJumboFramesCase01(TestJumboFramesTestCaseBase):
    """
    Test VM network with MTU 5000
    """
    __test__ = True
    net = conf.NETS[1][0]
    mtu_5000 = conf.MTU[1]

    @classmethod
    def setup_class(cls):
        """
        Attach VM network with MTU 5000 to host
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3718")
    def test_check_mtu(self):
        """
        Check physical and logical levels for network with Jumbo frames
        """
        helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net, mtu=self.mtu_5000
        )


class TestJumboFramesCase02(TestJumboFramesTestCaseBase):
    """
    Attach two non-VM VLAN networks with Jumbo Frames
    Removes one of the networks
    Check the correct values for the MTU in files
    """
    __test__ = True
    net_1 = conf.NETS[2][0]
    net_2 = conf.NETS[2][1]
    vlan_1 = conf.VLAN_IDS[0]
    vlan_2 = conf.VLAN_IDS[1]
    mtu_5000 = conf.MTU[1]
    mtu_9000 = conf.MTU[0]

    @classmethod
    def setup_class(cls):
        """
        Attach two non-VM VLAN networks with Jumbo Frames
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net_1,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": cls.net_2,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3721")
    def test_check_mtu_after_network_removal(self):
        """
        Remove one network from host
        Check physical and logical levels for networks with Jumbo frames
        """
        if not hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_2]
        ):
            raise conf.NET_EXCEPTION()

        helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_1, mtu=self.mtu_5000,
            vlan=self.vlan_1, bridge=False
        )


@attr(tier=2)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestJumboFramesCase03(TestJumboFramesTestCaseBase):
    """
    Check connectivity between two hosts
    Change BOND mode
    Add slave to BOND
    Check connectivity between two VMs
    """
    __test__ = True
    net = conf.NETS[3][0]
    mtu_5000 = conf.MTU[1]
    mtu_4500 = str(conf.SEND_MTU[0])
    bond = "bond3"
    ips = network_helper.create_random_ips(num_of_ips=4, mask=24)
    vm = conf.VM_0

    @classmethod
    def setup_class(cls):
        """
        Attach bridged network with MTU over bond to two hosts
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": cls.bond,
                    "slaves": None,
                    "ip": {
                        "1": {
                            "address": None,
                            "netmask": "24",
                            "boot_protocol": "static"
                        }
                    }
                },
            }
        }

        for host, nics, ip in zip(
            [conf.HOST_0_NAME, conf.HOST_1_NAME],
            [conf.HOST_0_NICS, conf.HOST_1_NICS],
            cls.ips[2:]
        ):
            network_dict["add"]["1"]["slaves"] = nics[2:4]
            network_dict["add"]["1"]["ip"]["1"]["address"] = ip
            if not hl_host_network.setup_networks(
                host_name=host, **network_dict
            ):
                raise conf.NET_EXCEPTION()

        helper.add_vnics_to_vms(
            ips=cls.ips[:2], network=cls.net, mtu=cls.mtu_5000
        )

    @polarion("RHEVM3-3732")
    def test_check_configurations_and_traffic(self):
        """
        Pass traffic between the hosts with configured MTU.
        """
        network_helper.send_icmp_sampler(
            host_resource=conf.VDS_0_HOST, dst=self.ips[3],
            size=self.mtu_4500
        )

    @polarion("RHEVM3-3713")
    def test_bond_mode_change(self):
        """
        Change BOND mode
        Check physical and logical levels for networks with Jumbo frames
        """
        network_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "mode": "4",
                },
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.check_logical_physical_layer(
            network=self.net,
            mtu=self.mtu_5000, bond=self.bond, bond_nic1=conf.HOST_0_NICS[2],
            bond_nic2=conf.HOST_0_NICS[3]
        )

    @polarion("RHEVM3-3716")
    def test_increasing_bond_nics(self):
        """
        Add slave to BOND
        Check physical and logical levels for networks with Jumbo frames
        """
        network_dict = {
            "update": {
                "1": {
                    "nic": self.bond,
                    "slaves": conf.HOST_0_NICS[1:4]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.check_logical_physical_layer(
            bond=self.bond, network=self.net, mtu=self.mtu_5000,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3]
        )

    @polarion("RHEVM3-3722")
    def test_check_traffic_on_vm_over_bond(self):
        """
        Send ping with MTU 4500 between the two VMS
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm)
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1], size=self.mtu_4500
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VMs
        """
        helper.remove_vnics_from_vms()
        super(TestJumboFramesCase03, cls).teardown_class()


@attr(tier=2)
@pytest.mark.skipif(
    conf.NOT_FOUR_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestJumboFramesCase04(TestJumboFramesTestCaseBase):
    """
    Attach 4 VLAN networks over BOND to two hosts
    Check that MTU is configured on the hosts
    Check connectivity between the hosts
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)
    bond = "bond12"
    net_1 = conf.NETS[4][0]
    net_2 = conf.NETS[4][1]
    net_3 = conf.NETS[4][2]
    net_4 = conf.NETS[4][3]
    vnic = conf.NIC_NAME[2]
    mtu_8500 = str(conf.SEND_MTU[1])
    mtu_9000 = conf.MTU[0]
    mtu_5000 = str(conf.MTU[1])
    vm = conf.VM_0

    @classmethod
    def setup_class(cls):
        """
        Attach 4 VLAN networks over BOND to two hosts
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net_1,
                    "nic": cls.bond,
                    "slaves": None,
                },
                "2": {
                    "network": cls.net_2,
                    "nic": cls.bond,
                    "ip": {
                        "1": {
                            "address": None,
                            "netmask": "24",
                            "boot_protocol": "static"
                        }
                    }
                },
                "3": {
                    "network": cls.net_3,
                    "nic": cls.bond,
                },
                "4": {
                    "network": cls.net_4,
                    "nic": cls.bond,
                },
            }
        }
        for host, nics, ip in zip(
            [conf.HOST_0_NAME, conf.HOST_1_NAME],
            [conf.HOST_0_NICS, conf.HOST_1_NICS],
            cls.ips
        ):
            network_dict["add"]["1"]["slaves"] = nics[2:4]
            network_dict["add"]["2"]["ip"]["1"]["address"] = ip
            if not hl_host_network.setup_networks(
                host_name=host, **network_dict
            ):
                raise conf.NET_EXCEPTION()

        helper.add_vnics_to_vms(
            ips=cls.ips, mtu=str(cls.mtu_9000), network=cls.net_2
        )
        helper.add_vnics_to_vms(
            ips=cls.ips, mtu=cls.mtu_5000, nic_name=cls.vnic,
            network=cls.net_1, set_ip=False
        )

    @polarion("RHEVM3-3736")
    def test_check_traffic_on_hosts_when_there_are_many_networks(self):
        """
        Check that MTU is configured on the hosts
        Check connectivity between the hosts
        """
        list_check_networks = [
            conf.HOST_0_NICS[2], conf.HOST_0_NICS[3], self.bond
        ]
        for element in list_check_networks:
            if not test_utils.check_configured_mtu(
                vds_resource=conf.VDS_0_HOST, mtu=str(self.mtu_9000),
                inter_or_net=element
            ):
                raise conf.NET_EXCEPTION()

        helper.check_logical_physical_layer(
            mtu=self.mtu_9000, bond=self.bond,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3],
            logical=False
        )
        network_helper.send_icmp_sampler(
            host_resource=conf.VDS_0_HOST, dst=self.ips[1],
            size=self.mtu_8500
        )

    @polarion("RHEVM3-3731")
    def test_check_traffic_on_vms_when_host_has_many_networks(self):
        """
        Send ping with MTU 8500 between the two VMs
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm)
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=self.mtu_8500
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        helper.remove_vnics_from_vms()
        helper.remove_vnics_from_vms(nic_name=cls.vnic)
        super(TestJumboFramesCase04, cls).teardown_class()


@attr(tier=2)
@pytest.mark.skipif(
    conf.NOT_FOUR_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestJumboFramesCase05(TestJumboFramesTestCaseBase):
    """
    Creates bridged VLAN network with 5000 MTU values
    and as display, Attaching the network to VMs and checking the traffic
    between them
    """
    __test__ = True
    ips = network_helper.create_random_ips(num_of_ips=4, mask=24)
    net = conf.NETS[5][0]
    mtu_5000 = str(conf.MTU[1])
    mtu_4500 = str(conf.SEND_MTU[0])
    vm = conf.VM_0

    @classmethod
    def setup_class(cls):
        """
        Update network to have display role
        Attach VLAN network (display role) to host NIC
        """
        if not ll_networks.update_cluster_network(
            positive=True, cluster=conf.CL_0, network=cls.net,
            usages='display,vm'
        ):
            raise conf.NET_EXCEPTION()

        network_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": None,
                    "ip": {
                        "1": {
                            "address": None,
                            "netmask": "24",
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        for host, nics, ip in zip(
            [conf.HOST_0_NAME, conf.HOST_1_NAME],
            [conf.HOST_0_NICS, conf.HOST_1_NICS],
            cls.ips[2:]
        ):
            network_dict["add"]["1"]["ip"]["1"]["address"] = ip
            network_dict["add"]["1"]["nic"] = nics[1]
            if not hl_host_network.setup_networks(
                host_name=host, **network_dict
            ):
                raise conf.NET_EXCEPTION()

        helper.add_vnics_to_vms(
            ips=cls.ips[:2], mtu=cls.mtu_5000, network=cls.net
        )

    @polarion("RHEVM3-3724")
    def test_check_traffic_on_vm_when_network_is_display(self):
        """
        Send ping between 2 VMS
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm)
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1], size=self.mtu_4500
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VMs
        Update ovirtmgmt to be display network
        """
        helper.remove_vnics_from_vms()
        ll_networks.update_cluster_network(
            positive=True, cluster=conf.CL_0, network=conf.MGMT_BRIDGE,
            usages="display,vm,migration,management"
        )
        super(TestJumboFramesCase05, cls).teardown_class()


class TestJumboFramesCase06(TestJumboFramesTestCaseBase):
    """
    Try to attach VM VLAN network and non-VM network with different MTU to the
    same BOND
    """
    __test__ = True
    net_1 = conf.NETS[6][0]
    net_2 = conf.NETS[6][1]
    bond = "bond6"

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

        if hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()


@attr(tier=2)
@pytest.mark.skipif(
    conf.NOT_FOUR_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestJumboFramesCase07(TestJumboFramesTestCaseBase):
    """
    Creates 2 bridged VLAN networks with different MTU and check traffic
    Check physical and logical levels for bridged VLAN networks
    between VMs over those networks
    """
    __test__ = True
    net_1 = conf.NETS[7][0]
    net_2 = conf.NETS[7][1]
    vlan_1 = conf.REAL_VLANS[0]
    vlan_2 = conf.REAL_VLANS[1]
    mtu_5000 = conf.MTU[1]
    mtu_9000 = conf.MTU[0]
    mtu_4500 = str(conf.SEND_MTU[0])
    vm_0 = conf.VM_0
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Attach two VLAN networks to host NIC with different MTU on two hosts
        Add vNICs to VM and configure IPs
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net_1,
                    "nic": None,
                },
                "2": {
                    "network": cls.net_2,
                    "nic": None
                }
            }
        }

        for host, nics in zip(
            [conf.HOST_0_NAME, conf.HOST_1_NAME],
            [conf.HOST_0_NICS, conf.HOST_1_NICS]
        ):
            network_dict["add"]["1"]["nic"] = nics[1]
            network_dict["add"]["2"]["nic"] = nics[1]
            if not hl_host_network.setup_networks(
                host_name=host, **network_dict
            ):
                raise conf.NET_EXCEPTION()

        helper.add_vnics_to_vms(
            ips=cls.ips, network=cls.net_1, mtu=cls.mtu_5000
        )

    @polarion("RHEVM3-3717")
    def test_check_mtu_values_in_files(self):
        """
        Check physical and logical levels for bridged VLAN networks
        """
        helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_1, mtu=self.mtu_5000,
            vlan=self.vlan_1, physical=False
        )
        helper.check_logical_physical_layer(
            nic=conf.HOST_0_NICS[1], network=self.net_2, mtu=self.mtu_9000,
            vlan=self.vlan_2
        )

    @polarion("RHEVM3-3720")
    def test_check_traffic_on_vms(self):
        """
        Send ping between 2 VMs
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm_0)
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=self.mtu_4500
        )

        for host_name in conf.HOST_0_NAME, conf.HOST_1_NAME:
            hl_host_network.remove_networks_from_host(
                host_name=host_name, networks=[self.net_2]
            )

        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=self.mtu_4500
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VMs
        Remove networks from the setup
        """
        helper.remove_vnics_from_vms()
        super(TestJumboFramesCase07, cls).teardown_class()


class TestJumboFramesCase08(TestJumboFramesTestCaseBase):
    """
    Attach bridged VLAN network over BOND on Host with MTU 5000
    Add another network with MTU 1500 to the BOND
    Check that MTU on NICs are configured correctly on the logical and
    physical layers.
    """
    __test__ = True
    net_1 = conf.NETS[8][0]
    net_2 = conf.NETS[8][1]
    vlan_1 = conf.VLAN_IDS[6]
    vlan_2 = conf.VLAN_IDS[7]
    mtu_5000 = conf.MTU[1]
    mtu_1500 = conf.MTU[3]
    bond = "bond8"

    @classmethod
    def setup_class(cls):
        """
        Attach bridged VLAN network over BOND on Host with MTU 5000
        """
        network_dict = {
            "add": {
                "1": {
                    "network": cls.net_1,
                    "nic": cls.bond,
                    "slaves": conf.HOST_0_NICS[2:4]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

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

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.check_logical_physical_layer(
            bond=self.bond, network=self.net_1, mtu=self.mtu_5000,
            bond_nic1=conf.HOST_0_NICS[2], bond_nic2=conf.HOST_0_NICS[3]
        )
        helper.check_logical_physical_layer(
            bond=self.bond, network=self.net_2, mtu=self.mtu_1500,
            physical=False
        )


class TestJumboFramesCase09(TestJumboFramesTestCaseBase):
    """
    Configure MTU 2000 on host NIC (via ssh)
    Attach network to the same host NIC without MTU
    Check that host NIC MTU is changed to 1500
    """
    __test__ = True
    mtu_2000 = str(conf.MTU[2])
    mtu_1500 = str(conf.MTU[3])
    net = conf.NETS[9][0]

    @classmethod
    def setup_class(cls):
        """
        Configure MTU 2000 on host NIC (via ssh)
        Attach network to the same host NIC without MTU
        """
        if not test_utils.configure_temp_mtu(
            vds_resource=conf.VDS_0_HOST, mtu=cls.mtu_2000,
            nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

        network_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_0_NICS[1],
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3734")
    def test_check_mtu_pre_configured(self):
        """
        Check that host NIC MTU is changed to 1500
        """
        if not test_utils.check_configured_mtu(
            vds_resource=conf.VDS_0_HOST, mtu=self.mtu_1500,
            inter_or_net=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()
