#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import pytest

import config as topologies_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import update_vnic_network
from rhevmtests.fixtures import (
    start_vms_fixture_function,
    stop_vms_fixture_function  # flake8: noqa
)
from rhevmtests.networking.fixtures import (
    NetworkFixtures,
    setup_networks_fixture_function,
    clean_host_interfaces_fixture_function  # flake8: noqa
)


@pytest.fixture(scope="module", autouse=True)
def topologies_prepare_setup(request):
    """
    prepare setup
    """
    topologies = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from engine")
        assert network_helper.remove_networks_from_setup(
            hosts=topologies.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Create networks on engine")
    network_helper.prepare_networks_on_setup(
        networks_dict=topologies_conf.NETS_DICT, dc=topologies.dc_0,
        cluster=topologies.cluster_0
    )


@attr(tier=2)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(
    setup_networks_fixture_function.__name__,
    update_vnic_network.__name__,
    start_vms_fixture_function.__name__,
)
class TestTopologiesVm(NetworkTest):
    """
    Check VM connectivity over:
    1. VLAN network
    2. VLAN over BOND with modes 1, 2, 4

    Check host connectivity over:
    1. BOND modes 0, 3, 5, 6
    """
    # General params
    vm_name = conf.VM_0

    # start_vm_function params
    vms = {
        vm_name: {
            "host": 0
        }
    }

    # test params [start VMs dict, network, sn dict, BOND mode]
    # VM tests
    # VLAN network params
    vm_vlan_net = topologies_conf.NETS[1][0]
    test_1_sn_dict = {
        0: {
            vm_vlan_net: {
                "nic": 1,
                "network": vm_vlan_net
            }
        }
    }
    vm_vlan_net_params = [vms, vm_vlan_net, test_1_sn_dict, None]

    # VLAN over BOND mode 1 params
    vm_vlan_bond_mode_1 = topologies_conf.NETS[1][1]
    test_2_sn_dict = {
        0: {
            vm_vlan_bond_mode_1: {
                "nic": "bond2",
                "network": vm_vlan_bond_mode_1,
                "slaves": [2, 3],
                "mode": 1
            }
        }
    }
    vm_vlan_bond_mode_1_params = [vms, vm_vlan_bond_mode_1, test_2_sn_dict, 1]

    # Bridge over BOND mode 2 params
    skip_ = pytest.mark.skip("No switch support for BOND mode 2")
    vm_bond_mode_2 = topologies_conf.NETS[1][2]
    test_3_sn_dict = {
        0: {
            vm_bond_mode_2: {
                "nic": "bond3",
                "network": vm_bond_mode_2,
                "slaves": [2, 3],
                "mode": 2
            }
        }
    }
    vm_bond_mode_2_params = [vms, vm_bond_mode_2, test_3_sn_dict, 2]

    # Bridge over BOND mode 4 params
    vm_bond_mode_4 = topologies_conf.NETS[1][3]
    test_4_sn_dict = {
        0: {
            vm_bond_mode_4: {
                "nic": "bond4",
                "network": vm_bond_mode_4,
                "slaves": [2, 3],
                "mode": 4
            }
        }
    }
    vm_bond_mode_4_params = [vms, vm_bond_mode_4, test_4_sn_dict, 4]

    # Non-VM tests
    # Non-VM over BOND mode 0 params
    bond_mode_0 = topologies_conf.NETS[1][4]
    test_5_sn_dict = {
        0: {
            bond_mode_0: {
                "nic": "bond5",
                "network": bond_mode_0,
                "slaves": [2, 3],
                "mode": 0,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }
    bond_mode_0_params = [None, None, test_5_sn_dict, 0]

    # Non-VM over BOND mode 3 params
    bond_mode_3 = topologies_conf.NETS[1][5]
    test_6_sn_dict = {
        0: {
            bond_mode_3: {
                "nic": "bond6",
                "network": bond_mode_3,
                "slaves": [2, 3],
                "mode": 3,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }
    bond_mode_3_params = [None, None, test_6_sn_dict, 3]

    # Non-VM over BOND mode 5 params
    bond_mode_5 = topologies_conf.NETS[1][6]
    test_7_sn_dict = {
        0: {
            bond_mode_5: {
                "nic": "bond7",
                "network": bond_mode_5,
                "slaves": [2, 3],
                "mode": 5,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }
    bond_mode_5_params = [None, None, test_7_sn_dict, 5]

    # Non-VM over BOND mode 0 params
    bond_mode_6 = topologies_conf.NETS[1][7]
    test_8_sn_dict = {
        0: {
            bond_mode_6: {
                "nic": "bond8",
                "network": bond_mode_6,
                "slaves": [2, 3],
                "mode": 6,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }
    bond_mode_6_params = [None, None, test_8_sn_dict, 6]

    @pytest.mark.parametrize(
        ("start_vms_dict", "network", "hosts_nets_nic_dict", "mode"),
        [
            # VM tests
            polarion("RHEVM3-12286")(vm_vlan_net_params),
            polarion("RHEVM3-12290")(vm_vlan_bond_mode_1_params),
            # TODO: Enable when we have switch BOND mode 2 support
            # polarion("RHEVM3-12293")(vm_bond_mode_2_params),
            polarion("RHEVM3-12299")(vm_bond_mode_4_params),

            # Non-VM tests
            polarion("RHEVM3-12289")(bond_mode_0_params),
            polarion("RHEVM3-12297")(bond_mode_3_params),
            polarion("RHEVM3-12302")(bond_mode_5_params),
            polarion("RHEVM3-12303")(bond_mode_6_params),
        ],
        ids=[
            # VM tests
            "VLAN network over host NIC",
            "VLAN network over BOND mode 1",
            # TODO: Enable when we have switch BOND mode 2 support
            # "Bridge network over BOND mode 2",
            "Bridge network over BOND mode 4",

            # Non-VM tests
            "Non-VM network over BOND mode 0",
            "Non-VM network over BOND mode 3",
            "Non-VM network over BOND mode 5",
            "Non-VM network over BOND mode 6",
        ]
    )
    def test_check_vm_connectivity(
        self, start_vms_dict, network, hosts_nets_nic_dict, mode
    ):
        """
        Test VM connectivity over:
        1. VLAN network
        2. VLAN over BOND with modes 1, 2, 4
        """
        vm_net_list = [self.vm_vlan_net, self.vm_vlan_net_params]
        vlan = True if network in vm_net_list else False
        testflow.step(
            "Check connectivity: %s %s network",
            "VLAN" if vlan else "", "over BOND mode %s" % mode if mode else ""
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, vlan=vlan, mode=mode,
            vm=False if not network else True, flags="-r" if not network
            else None
        )
