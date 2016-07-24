#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network migration feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Network migration will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks
"""

import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.virt.helper as helper
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa
from rhevmtests.virt.migration.fixtures import (
    migration_init, add_nic_to_vm, update_migration_network_on_cluster,
    network_migrate_init
)
import migration_helper
import config


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationNetworkCase01(NetworkTest):
    """
    Check that network migration 1 VMs over NIC is working as
    expected by putting NIC with required network down
    """
    __test__ = True
    config.NET_1 = config.NETS[1][0]
    config.NET_2 = config.NETS[1][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3878")
    def test_migration_nic(self):
        testflow.step(
            "Check that network migration 1 VMs over NIC is working as "
            "expected by putting NIC with required network down"
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], req_nic=2
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase02(NetworkTest):
    """
    Verify dedicated migration over tagged network over NIC
    """
    __test__ = True
    config.NET_1 = config.NETS[2][0]
    config.NET_2 = config.NETS[2][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3851")
    def test_dedicated_tagged_migration(self):
        testflow.step(
            "Check that VLAN network migration over NIC is working as expected"
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], vlan=config.REAL_VLANS[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase03(NetworkTest):
    """
    Verify dedicated migration over non-VM network over NIC
    """

    __test__ = True
    config.NET_1 = config.NETS[3][0]
    config.NET_2 = config.NETS[3][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3849")
    def test_nonvm_migration(self):
        """
        Check dedicated migration over non-VM network over NIC
        """
        testflow.step(
            "Check that non-VM network migration over NIC is working as "
            "expected"
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], non_vm=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase04(NetworkTest):
    """
    Verify dedicated regular network migration when its also display network
    """
    __test__ = True
    config.NET_1 = config.NETS[4][0]
    config.NET_2 = config.NETS[4][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3885")
    def test_dedicated_migration_display(self):
        testflow.step(
            "Check that network migration over NIC is working as "
            "expected when the network is also the display network"
        )
        helper.migrate_vms_and_check_traffic(vms=[self.vm_name])


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__,
    add_nic_to_vm.__name__
)
class TestMigrationCase05(NetworkTest):
    """
    Verify dedicated regular network migration when the net reside on the VM
    """
    __test__ = True

    config.NET_1 = config.NETS[5][0]
    config.NET_2 = config.NETS[5][1]
    network = migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    # NIC to VM
    nic = 'nic2'
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3847")
    def test_dedicated_migration_reside_vm(self):
        testflow.step(
            "Check that network migration over NIC is working as "
            "expected when the network also resides on the VM"
        )
        helper.migrate_vms_and_check_traffic(vms=[self.vm_name])


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase06(NetworkTest):
    """
    Verify migration over mgmt network when migration network is not attached
    to Hosts. Migration Network is attached only to DC and Cluster
    """
    __test__ = True
    migration_network = config.NETS[6][0]
    networks = list()

    @polarion("RHEVM3-3847")
    def test_mgmt_network_migration(self):
        testflow.step(
            "Verify migration over mgmt network when migration network"
            " is not attached to Hosts"
        )
        helper.migrate_vms_and_check_traffic(
            vms=[config.MIGRATION_VM], nic_index=0
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase07(NetworkTest):
    """
    Verify dedicated regular network migration over Bond
    """
    __test__ = True
    config.NET_1 = config.NETS[7][0]
    config.NET_2 = config.NETS[7][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    bond70 = 'bond70'
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=networks,
        hosts=2,
        bond_name=bond70
    )

    @polarion("RHEVM3-3848")
    def test_dedicated_migration_bond(self):
        testflow.step(
            "Check that network migration over Bond is working as expected "
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], bond=self.bond70
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase08(NetworkTest):
    """
    Verify dedicated regular non-vm network migration over Bond
    """
    __test__ = True
    config.NET_1 = config.NETS[8][0]
    config.NET_2 = config.NETS[8][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    bond80 = 'bond80'
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=networks,
        hosts=2,
        bond_name=bond80
    )

    @polarion("RHEVM3-3850")
    def test_dedicated_migration_nonvm_bond(self):
        testflow.step(
            "Check that non-VM network migration over Bond is working "
            "as expected "
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], bond=self.bond80, non_vm=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase09(NetworkTest):
    """
    Verify dedicated regular tagged network migration over Bond
    """
    __test__ = True
    config.NET_1 = config.NETS[9][0]
    config.NET_2 = config.NETS[9][1]
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    vm_name = config.MIGRATION_VM
    bond90 = 'bond90'
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT_WITH_BONDS,
        networks=networks,
        hosts=2,
        bond_name=bond90
    )

    @polarion("RHEVM3-3852")
    def test_dedicated_migration_vlan_bond(self):
        testflow.step(
            "Check that VLAN network migration over Bond is working as "
            "expected "
        )
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], vlan=config.REAL_VLANS[1],
            bond=self.bond90
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase10(NetworkTest):
    """
    Verify  migration over mgmt network when dedicated migration network is
    replaced with display network
    """
    __test__ = True
    config.NET_1 = config.NETS[10][0]
    config.NET_2 = config.NETS[10][1]
    vm_name = config.MIGRATION_VM
    migration_network = config.NET_1
    networks = [config.NET_1, config.NET_2]
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOSTS_NETS_NIC_DICT,
        networks=networks,
        hosts=2
    )

    @polarion("RHEVM3-3859")
    def test_tmgmt_network_migration(self):
        """
        Check migration over mgmt network when migration network is changed to
        display
        """
        testflow.step(
            "Replace migration from the network %s with display network",
            config.NETS[10][0]
        )
        assert (ll_networks.update_cluster_network(
            True, cluster=config.CLUSTER_NAME[0],
            network=config.NETS[10][0],
            usages="display"
        ), "Cannot update network usages param"
        )

        testflow.step("Make sure the migration is over mgmt network")
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], nic_index=0
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    network_migrate_init.__name__,
    setup_networks_fixture.__name__,
    update_migration_network_on_cluster.__name__
)
class TestMigrationCase11(NetworkTest):
    """
    Verify when dedicated regular network migration is not configured on the
    Host the migration will occur on the mgmt network network
    """
    __test__ = True
    config.NET_1 = config.NETS[11][0]
    vm_name = config.MIGRATION_VM
    migration_network = config.NET_1
    networks = [config.NET_1]
    hosts_nets_nic_dict = migration_helper.init_network_dict(
        hosts_nets_nic_dict=config.HOST_NET_NIC_DICT,
        networks=networks,
        hosts=1
    )

    @polarion("RHEVM3-3872")
    def test_dedicated_migration_mgmt(self):
        testflow.step("Make sure the migration is over mgmt network")
        helper.migrate_vms_and_check_traffic(
            vms=[self.vm_name], nic_index=0
        )
