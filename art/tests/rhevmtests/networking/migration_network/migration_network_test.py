#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration Network feature tests

The following elements will be used during the testing:
1 DC, 1 Cluster, 2 Hosts (all rest will be set in maintenance mode), BONDs,
VLANs, host networks, VM and non-VM networks
"""
import config as mig_config

import pytest

import config
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, tier2
from fixtures import (
    update_network_usages,
    deactivate_hosts,
    add_vnic_to_vms,
    remove_networks
)
from rhevmtests import helpers
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (  # noqa: F401
    create_and_attach_networks,
    remove_all_networks,
    setup_networks_fixture_function,
    clean_host_interfaces_fixture_function
)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture_function.__name__,
    update_network_usages.__name__,
    remove_networks.__name__,
    start_vm.__name__,
    add_vnic_to_vms.__name__,
    deactivate_hosts.__name__,
)
class TestMigrationNetwork(NetworkTest):
    """
    Test Migration Network feature:
    1. Test migration on non-operational host
    2. Test migration on dedicated VLAN network
    3. Test migration on non-VM network
    4. Test migration on display and migration network
    5. Test migration on network used by VM
    6. Test migration on network on bond
    7. Test migration on non-VM network on bond
    8. Test migration on VLAN network with bond
    9. Test migration on display network
    10. Test migration to host without migration network
    11. Test migration on IPv6 address
    """
    # Test VM setting
    vm = config.VM_NAME

    # clean_host_interfaces_fixture_function fixture params
    hosts_nets_nic_dict = {
        0: {},
        1: {}
    }

    # start_vm fixture params
    start_vms_dict = {
        vm: {
            "host": 1
        }
    }

    # create_and_attach_networks fixture parameters
    create_networks = {
        "1": {
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
            "networks": mig_config.CREATE_NETWORKS_DICT
        }
    }
    remove_dcs_networks = [conf.DC_0]

    # Test case parameters = [
    #   Test case setup network dict,
    #   migrate_vms_and_check_traffic function parameters,
    #   Usages to be set on the migration network,
    #   add_vnic_to_vm fixture parameters
    # ]

    # Migration network on non-operational host test params
    # In this case, VM migration will occur automatically to the next available
    # host when its origin host becomes non-operational
    non_op_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_TWO_NIC_DICT,
        networks=config.NETS[1][:2], hosts=2
    )
    non_op_params = [
        non_op_host_networks,
        {"req_nic": 2},
        {config.NETS[1][0]: "migration"},
        {}
    ]

    # Migration network on dedicated VLAN network test params
    network_vlan_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[2][0]], hosts=2
    )
    network_vlan_params = [
        network_vlan_host_networks,
        {"vlan": config.VLAN_CASE_2},
        {config.NETS[2][0]: "migration"},
        {}
    ]

    # Migration network on non-VM network test params
    network_non_vm_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[3][0]], hosts=2
    )
    network_non_vm_params = [
        network_non_vm_host_networks,
        {"non_vm": True},
        {config.NETS[3][0]: "migration"},
        {}
    ]

    # Migration network on network used by VM test params
    migration_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[4][0]], hosts=2
    )
    migration_params = [
        migration_host_networks,
        {},
        {config.NETS[4][0]: "migration,display"},
        {}
    ]

    # Migration network on network used by VM test params
    vm_used_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[5][0]], hosts=2
    )
    vm_used_migration_network = config.NETS[5][0]
    vm_used_params = [
        vm_used_host_networks,
        {},
        {config.NETS[5][0]: "migration"},
        {
            vm: {
                "name": config.VM_MIG_VNIC,
                "network": vm_used_migration_network
            }
        }
    ]

    # Migration network on network on bond test params
    bond_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[config.NETS[6][0]], hosts=2, bond=config.BOND_CASE_6
    )
    bond_params = [
        bond_host_networks,
        {"bond": config.BOND_CASE_6},
        {config.NETS[6][0]: "migration"},
        {}
    ]

    # Migration network on non-VM network on bond test params
    bond_non_vm_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[config.NETS[7][0]], hosts=2, bond=config.BOND_CASE_7
    )
    bond_non_vm_params = [
        bond_non_vm_host_networks,
        {
            "bond": config.BOND_CASE_7,
            "non_vm": True
        },
        {config.NETS[7][0]: "migration"},
        {}
    ]

    # Migration network on VLAN network with bond test params
    bond_vlan_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[config.NETS[8][0]], hosts=2,
        bond=config.BOND_CASE_8
    )
    bond_vlan_params = [
        bond_vlan_host_networks,
        {
            "bond": config.BOND_CASE_8,
            "vlan": config.VLAN_CASE_8
        },
        {config.NETS[8][0]: "migration"},
        {}
    ]

    # Migration network on dedicated network as display network test params
    dedicated_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[9][0]], hosts=2
    )
    dedicated_params = [
        dedicated_host_networks,
        {"nic_index": 0},
        {config.NETS[9][0]: "display"},
        {}
    ]

    # Migration to host without migration network
    host_no_mig_net_host_networks = helper.prepare_sn_dict(
        template=config.HOST_NET_NIC_DICT,
        networks=[config.NETS[10][0]], hosts=1
    )
    host_no_mig_net_params = [
        host_no_mig_net_host_networks,
        {"nic_index": 0},
        {config.NETS[10][0]: "migration"},
        {}
    ]

    # Migration network on IPv6 network test params
    network_ipv6_host_networks = helper.prepare_sn_dict(
        template=config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[config.NETS[11][0]], hosts=2, ipv6=True
    )
    network_ipv6_params = [
        network_ipv6_host_networks,
        {"ipv6": True},
        {config.NETS[11][0]: "migration"},
        {}
    ]

    @tier2
    @pytest.mark.parametrize(
        (
         "hosts_nets_nic_dict",
         "migrate_vms_and_check_traffic_params",
         "update_network_usages_params",
         "add_vnic_to_vms_params"
         ),
        [
            pytest.param(*non_op_params, marks=(polarion("RHEVM3-3878"))),
            pytest.param(
                *network_vlan_params, marks=(polarion("RHEVM3-3851"))
            ),
            pytest.param(
                *network_non_vm_params, marks=(polarion("RHEVM3-3849"))
            ),
            pytest.param(*migration_params, marks=(polarion("RHEVM3-3885"))),
            pytest.param(*vm_used_params, marks=(polarion("RHEVM3-3886"))),
            pytest.param(*bond_params, marks=(polarion("RHEVM3-3848"))),
            pytest.param(*bond_non_vm_params, marks=(polarion("RHEVM3-3850"))),
            pytest.param(*bond_vlan_params, marks=(polarion("RHEVM3-3852"))),
            pytest.param(*dedicated_params, marks=(polarion("RHEVM3-3859"))),
            pytest.param(
                *host_no_mig_net_params, marks=(polarion("RHEVM3-3872"))
            ),
            pytest.param(
                *network_ipv6_params, marks=(polarion("RHEVM3-21572"))
            ),
        ],
        ids=[
            "migration_network_on_non_operational_host",
            "migration_network_on_dedicated_vlan_network",
            "migration_network_on_non_vm_network",
            "migration_network_on_display_and_migration_network",
            "migration_network_on_network_used_by_vm",
            "migration_network_on_network_on_bond",
            "migration_network_on_non_vm_network_on_bond",
            "migration_network_on_vlan_network_with_bond",
            "migration_network_on_dedicated_network_as_display_network",
            "migration_network_on_host_without_migration_network",
            "migration_network_on_ipv6_address"
        ]
    )
    def test_migration_network(
        self, hosts_nets_nic_dict, migrate_vms_and_check_traffic_params,
        update_network_usages_params, add_vnic_to_vms_params
    ):
        """
        Test case for Migration Network
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_migration_network.parametrize,
            params=[
                hosts_nets_nic_dict, migrate_vms_and_check_traffic_params,
                update_network_usages_params, add_vnic_to_vms_params
            ]
        )
        testflow.step(_id)
        assert helper.check_migration_network(
            vms=[self.vm], **migrate_vms_and_check_traffic_params
        )
