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

import helper
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    update_network_usages, deactivate_hosts, add_vnic_to_vm, remove_networks
)
from rhevmtests import helpers
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces_fixture_function,
    NetworkFixtures,
    setup_networks_fixture_function
)


@pytest.fixture(scope="module", autouse=True)
def migration_network_prepare_setup(request):
    """
    Prepare networks setup for tests
    """
    mig = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(hosts=mig.hosts_list)
    request.addfinalizer(fin)

    testflow.setup("Create networks on setup")
    network_helper.prepare_networks_on_setup(
        networks_dict=mig_config.SETUP_NETWORKS_DICT, dc=mig.dc_0,
        cluster=mig.cluster_0
    )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    setup_networks_fixture_function.__name__,
    update_network_usages.__name__,
    remove_networks.__name__,
    start_vm.__name__,
    add_vnic_to_vm.__name__,
    deactivate_hosts.__name__,
)
class TestMigrationNetwork(NetworkTest):
    """
    Tests Migration Network feature

    1. Test migration network with non-operational host
    2. Test migration network with dedicated VLAN network
    3. Test migration network with non-VM network
    4. Test migration network with display and migration network
    5. Test migration network with network used by VM
    6. Test migration network with network on bond
    7. Test migration network with non-VM network on bond
    8. Test migration network with VLAN network on bond
    9. Test migration network with dedicated network as display network
    10. Test migration network with dedicated migration network and migration
        to host without migration network
    """

    # Test case parameters = [
    #   Host networks dict for SN fixture,
    #   migrate_vms_and_check_traffic helper function parameters,
    #   Network usages to be updated on migration network,
    #   add_vnic_to_vm fixture parameters
    # ]

    # Test VM setting
    vm = mig_config.VM_NAME

    # clean_host_interfaces_fixture_function fixture params
    hosts_nets_nic_dict = mig_config.CLEANUP_HOSTS_SETUP_DICT

    # start_vm fixture params
    start_vms_dict = {
        vm: {
            "host": mig_config.VM_ORIGIN_HOSTER_INDEX
        }
    }

    # Migration Network with non-operational host test params
    # In this case migration will occur automatically to the next available
    # host when hoster becomes non-operational
    non_op_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_TWO_NIC_DICT,
        networks=mig_config.NETS[1][:2], hosts=2
    )
    non_op_migrate_vm_params = {
        "req_nic": 2
    }
    non_op_update_network_usages_params = {
        mig_config.NETS[1][0]: "migration"
    }
    non_op_params = [
        non_op_host_networks, non_op_migrate_vm_params,
        non_op_update_network_usages_params, dict()
    ]

    # Migration Network with dedicated VLAN network test params
    network_vlan_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[mig_config.NETS[2][0]], hosts=2
    )
    network_vlan_migrate_vm_parms = {
        "vlan": mig_config.VLAN_CASE_2
    }
    network_update_network_usages_params = {
        mig_config.NETS[2][0]: "migration"
    }
    network_vlan_params = [
        network_vlan_host_networks, network_vlan_migrate_vm_parms,
        network_update_network_usages_params, dict()
    ]

    # Migration Network with non-VM network test params
    network_non_vm_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[mig_config.NETS[3][0]], hosts=2
    )
    network_non_vm_migrate_vm_params = {
        "non_vm": True
    }
    network_non_vm_update_network_usages_params = {
        mig_config.NETS[3][0]: "migration"
    }
    network_non_vm_params = [
        network_non_vm_host_networks, network_non_vm_migrate_vm_params,
        network_non_vm_update_network_usages_params, dict()
    ]

    # Migration Network with network used by VM test params
    migration_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[mig_config.NETS[4][0]], hosts=2
    )
    migration_update_network_usages_params = {
        mig_config.NETS[4][0]: "migration,display"
    }
    migration_params = [
        migration_host_networks, dict(),
        migration_update_network_usages_params, dict()
    ]

    # Migration Network with network used by VM test params
    vm_used_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[mig_config.NETS[5][0]], hosts=2
    )
    vm_used_migration_network = mig_config.NETS[5][0]
    vm_used_add_vnics_vms = {
        vm: {
            "name": mig_config.VM_ADDITIONAL_VNIC,
            "network": vm_used_migration_network
        }
    }
    vm_used_vm_update_network_usages_params = {
        mig_config.NETS[5][0]: "migration"
    }
    vm_used_params = [
        vm_used_host_networks, dict(), vm_used_vm_update_network_usages_params,
        vm_used_add_vnics_vms
    ]

    # Migration Network with network on bond test params
    bond_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[mig_config.NETS[6][0]], hosts=2, bond=mig_config.BOND_CASE_6
    )
    bond_migrate_vm_params = {
        "bond": mig_config.BOND_CASE_6
    }
    bond_vm_update_network_usages_params = {
        mig_config.NETS[6][0]: "migration"
    }
    bond_params = [
        bond_host_networks, bond_migrate_vm_params,
        bond_vm_update_network_usages_params, dict()
    ]

    # Migration Network with non-VM network on bond test params
    bond_non_vm_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[mig_config.NETS[7][0]], hosts=2, bond=mig_config.BOND_CASE_7
    )
    bond_non_vm_migrate_vm_params = {
        "bond": mig_config.BOND_CASE_7,
        "non_vm": True
    }
    bond_non_vm_update_network_usages_params = {
        mig_config.NETS[7][0]: "migration"
    }
    bond_non_vm_params = [
        bond_non_vm_host_networks, bond_non_vm_migrate_vm_params,
        bond_non_vm_update_network_usages_params, dict()
    ]

    # Migration Network with VLAN network on bond test params
    bond_vlan_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=[mig_config.NETS[8][0]], hosts=2,
        bond=mig_config.BOND_CASE_8
    )
    bond_vlan_migrate_vm_params = {
        "bond": mig_config.BOND_CASE_8,
        "vlan": mig_config.VLAN_CASE_8
    }
    bond_vlan_update_network_usages_params = {
        mig_config.NETS[8][0]: "migration"
    }
    bond_vlan_params = [
        bond_vlan_host_networks, bond_vlan_migrate_vm_params,
        bond_vlan_update_network_usages_params, dict()
    ]

    # Migration Network with dedicated network as display network test params
    dedicated_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOSTS_NETS_ONE_NIC_DICT,
        networks=[mig_config.NETS[9][0]], hosts=2
    )
    dedicated_migrate_vm_params = {
        "nic_index": 0
    }
    dedicated_update_network_usages_params = {
        mig_config.NETS[9][0]: "display"
    }
    dedicated_test_step = (
        "Testing migration of dedicated display network: %s"
        % mig_config.NETS[9][0]
    )
    dedicated_params = [
        dedicated_host_networks, dedicated_migrate_vm_params,
        dedicated_update_network_usages_params, dict()
    ]

    # Migration Network with migration network on host without migration
    # network test params
    host_no_mig_net_host_networks = helper.init_host_sn_dict(
        template_dict=mig_config.HOST_NET_NIC_DICT,
        networks=[mig_config.NETS[10][0]], hosts=1
    )
    host_no_mig_net_migrate_vm_params = {
        "nic_index": 0
    }
    host_no_mig_net_update_network_usages_params = {
        mig_config.NETS[10][0]: "migration"
    }
    host_no_mig_net_params = [
        host_no_mig_net_host_networks, host_no_mig_net_migrate_vm_params,
        host_no_mig_net_update_network_usages_params, dict()
    ]

    @pytest.mark.parametrize(
        (
         "hosts_nets_nic_dict", "test_migrate_param",
         "update_network_usages_param", "add_vnic_to_vm_param"
         ),
        [
            polarion("RHEVM3-3878")(non_op_params),
            polarion("RHEVM3-3851")(network_vlan_params),
            polarion("RHEVM3-3849")(network_non_vm_params),
            polarion("RHEVM3-3885")(migration_params),
            polarion("RHEVM3-3886")(vm_used_params),
            polarion("RHEVM3-3848")(bond_params),
            polarion("RHEVM3-3850")(bond_non_vm_params),
            polarion("RHEVM3-3852")(bond_vlan_params),
            polarion("RHEVM3-3859")(dedicated_params),
            polarion("RHEVM3-3872")(host_no_mig_net_params)
        ],
        ids=[
            "Test Migration Network with non-operational host",
            "Test Migration Network with dedicated VLAN network",
            "Test Migration Network with non-VM network",
            "Test Migration Network with display and migration network",
            "Test Migration Network with network used by VM",
            "Test Migration Network with network on bond",
            "Test Migration Network with non-VM network on bond",
            "Test Migration Network with VLAN network on bond",
            "Test Migration Network with dedicated network as display network",
            (
                "Test Migration Network with migration network on host "
                "without migration network"
            )
        ]
    )
    def test_migration_network(
        self, hosts_nets_nic_dict, test_migrate_param,
        update_network_usages_param, add_vnic_to_vm_param
    ):
        """
        Test case for Migration Network
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_migration_network.parametrize,
            params=[
                hosts_nets_nic_dict, test_migrate_param,
                update_network_usages_param, add_vnic_to_vm_param
            ]
        )

        testflow.step(_id)
        assert helper.check_migration_network(
            vms=[self.vm], **test_migrate_param
        )
