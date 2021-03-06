#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import pytest

import config as topologies_conf
import helper as topologies_helper
from art.test_handler.tools import polarion
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)
from fixtures import update_vnic_network
from rhevmtests import helpers
import rhevmtests.networking.config as conf

from rhevmtests.fixtures import (  # noqa: F401
    stop_vms_fixture_function,
    start_vms_fixture_function,
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces_fixture_function,
    setup_networks_fixture_function,
    create_and_attach_networks,
    remove_all_networks
)


@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
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
    dc = conf.DC_0

    # start_vm_function params
    vms = {
        vm_name: {
            "host": 0
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": topologies_conf.NETS_DICT
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

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

    @tier2
    @pytest.mark.parametrize(
        ("start_vms_dict", "network", "hosts_nets_nic_dict", "mode"),
        [
            # VM tests
            pytest.param(
                *vm_vlan_net_params, marks=(polarion("RHEVM3-12286"))
            ),
            pytest.param(
                *vm_vlan_bond_mode_1_params, marks=(polarion("RHEVM3-12290"))
            ),
            # TODO: Enable when we have switch BOND mode 2 support
            # pytest.param(
            #     *vm_bond_mode_2_params, marks=(polarion("RHEVM3-12293"))
            # ),
            pytest.param(
                *vm_bond_mode_4_params, marks=(polarion("RHEVM3-12299"))
            ),

            # Non-VM tests
            pytest.param(
                *bond_mode_0_params, marks=(polarion("RHEVM3-12289"))
            ),
            pytest.param(
                *bond_mode_3_params, marks=(polarion("RHEVM3-12297"))
            ),
            pytest.param(
                *bond_mode_5_params, marks=(polarion("RHEVM3-12302"))
            ),
            pytest.param(
                *bond_mode_6_params, marks=(polarion("RHEVM3-12303"))
            ),
        ],
        ids=[
            # VM tests
            "Check_connectivity_VLAN_network_over_host_NIC",
            "Check_connectivity_VLAN_network_over_BOND_mode_1",
            # TODO: Enable when we have switch BOND mode 2 support
            # "Check_connectivity_bridge_network_over_BOND_mode_2",
            "Check_connectivity_bridge_network_over_BOND_mode_4",

            # Non-VM tests
            "Check_connectivity_Non-VM_network_over_BOND_mode_0",
            "Check_connectivity_Non-VM_network_over_BOND_mode_3",
            "Check_connectivity_Non-VM_network_over_BOND_mode_5",
            "Check_connectivity_Non-VM_network_over_BOND_mode_6",
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

        _id = helpers.get_test_parametrize_ids(
            item=self.test_check_vm_connectivity.parametrize,
            params=[start_vms_dict, network, hosts_nets_nic_dict, mode]
        )
        testflow.step(_id)
        assert topologies_helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, vlan=vlan, mode=mode,
            vm=False if not network else True, flags="-r" if not network
            else None
        )
