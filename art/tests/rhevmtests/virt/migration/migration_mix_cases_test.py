#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import logging
import time
import pytest
from art.test_handler.tools import polarion
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.unittest_lib import attr, VirtTest, testflow
import rhevmtests.virt.helper as virt_helper
from rhevmtests.virt.migration.fixtures import (
    migration_init,
    restore_default_policy_on_cluster,
    restore_default_policy_on_vm,
    start_vms_on_specific_host,
    migration_load_test,
    migration_with_two_disks,
)
import config
import migration_helper

logger = logging.getLogger("virt_migration_mix_cases")


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    start_vms_on_specific_host.__name__
)
class TestMigrationMixCase1(VirtTest):
    """
    1. Start all VMs (2 VMs on host_1, 2 VMs on host_2)
    2. Bidirectional vms migration between two hosts (simultaneous)
    3. Stop VMs
    """
    __test__ = True

    @polarion("RHEVM3-5646")
    def test_bidirectional_migration_between_two_hosts(self):
        testflow.step("Test bidirectional vms migration between two hosts")
        assert virt_helper.migration_vms_to_diff_hosts(
            vms=config.VM_NAME[1:5]
        ), "Failed to migration all VMs"


@attr(tier=3)
@pytest.mark.usefixtures(
    migration_init.__name__,
    migration_load_test.__name__
)
class TestMigrationMixCase2(VirtTest):
    """
    1. Set VM memory to 85% of host memory
    2. Migrate VM
    Note: VM will run load on memory as part of test to simulate
    real working station
    """
    __test__ = True
    vm_name = config.MIGRATION_VM_LOAD
    load_of_2_gb = 2000
    time_to_run_load = 120

    @polarion("RHEVM3-14033")
    def test_migrate_vm_with_large_memory(self):
        testflow.step("Run load on VM, migrate VM.")
        virt_helper.load_vm_memory_with_load_tool(
            vm_name=self.vm_name, load=self.load_of_2_gb,
            time_to_run=self.time_to_run_load
        )
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_name
        ), "Failed to migrate VM with large memory"


@attr(tier=3)
@pytest.mark.usefixtures(
    migration_init.__name__,
    migration_with_two_disks.__name__
)
class TestMigrationMixCase3(VirtTest):
    """
    1. Add to VM 2 disks and migrate VM
    2. Remove disks in the end
    """
    __test__ = True
    vm_name = "VM_with_2_disks"

    @polarion("RHEVM3-5647")
    def test_migrate_vm_with_more_then_one_disk(self):
        testflow.step("Migrate VM with more then one disk")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name,
            wait=True
        ), "Failed to migrate VM with more then 1 disk"


@attr(tier=2)
@pytest.mark.usefixtures(migration_init.__name__)
class TestMigrationMixCase4(VirtTest):
    """
    In migration the destination host saves memory and CPU for the new VM,
    This test checks that those resources released at host after
    Migration finished, in order to check the pending resources
    We run query on DB. We get the resource status before and after migration.
    If resources are released the after list should be equals to the before,
    which is empty.
    """
    __test__ = True
    sql = "select vds_name,pending_vmem_size,pending_vcpus_count from vds;"
    vm_name = config.MIGRATION_VM

    @polarion("RHEVM3-5619")
    def test_check_DB_resources(self):
        """
        1. Get resource status before migration
        2. Migration VM
        3. Get resource status after migration
        4. Compare resource status
        """
        table_before = config.ENGINE.db.psql(sql=self.sql)
        logger.info(
            "Resource status before migration, \nResults: %s", table_before
        )
        testflow.step("Start vm migration")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name
        ), "Failed to migration VM: %s " % self.vm_name
        table_after = config.ENGINE.db.psql(sql=self.sql)
        logger.info(
            "Resource status after migration, \nResults: %s", table_after
        )
        testflow.step("Compare results")
        assert virt_helper.compare_resources_lists(
            table_before, table_after
        ), "Found resource that are pended to hosts"


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    restore_default_policy_on_cluster.__name__
)
class TestClusterLevelMigrationPoliciesAndBandwidth(VirtTest):
    """
    Update migration policy and bandwidth on cluster lever
    And migrate VM.
    """

    __test__ = True

    @polarion("RHEVM-16922")
    def test_migration_with_policy_bandwidth_auto(self):
        """
        Migrate with bandwidth auto and all policies
        """
        for migration_policy in config.MIGRATION_POLICY_NAME:
            testflow.step(
                "Migrate vm with policy: %s and bandwidth: %s",
                migration_policy, config.MIGRATION_BANDWIDTH_AUTO
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                bandwidth_method=config.MIGRATION_BANDWIDTH_AUTO,
                cluster_name=config.CLUSTER_NAME[0]
            ), "Failed to migrate VM: %s with policy %s" % (
                config.MIGRATION_VM, migration_policy
            )
            time.sleep(15)

    @polarion("RHEVM-16923")
    def test_migration_with_policy_bandwidth_hypervisor_default(self):
        """
        Migrate with bandwidth hypervisor default (52 Mbps) and all policies,
        check bandwidth with visrh domjobinfo
        """
        for migration_policy in config.MIGRATION_POLICY_NAME:
            testflow.step(
                "Migrate vm with policy: %s and bandwidth: %s, and check "
                "bandwidth",
                migration_policy, config.MIGRATION_BANDWIDTH_HYPERVISOR_DEFAULT
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                bandwidth_method=config.MIGRATION_BANDWIDTH_HYPERVISOR_DEFAULT,
                expected_bandwidth=config.HYPERVISOR_DEFAULT_BANDWIDTH,
                cluster_name=config.CLUSTER_NAME[0]
            ), "Failed to migrate VM: %s with policy %s" % (
                config.MIGRATION_VM, migration_policy
            )
            time.sleep(15)

    @polarion("RHEVM-16924")
    def test_migration_with_policy_custom_bandwidth_32_mbps(self):
        """
        Migrate with custom bandwidth 32 Mbps and all policies,
        check bandwidth with visrh domjobinfo
        """
        for migration_policy in config.MIGRATION_POLICY_NAME:
            testflow.step(
                "Migrate vm with policy: %s and BW custom: 32 Mbps and check "
                "bandwidth",
                migration_policy
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                bandwidth_method=config.MIGRATION_BANDWIDTH_CUSTOM,
                custom_bandwidth=config.CUSTOM_BW_32_MBPS,
                expected_bandwidth=config.CUSTOM_BW_32_MBPS / 2,
                cluster_name=config.CLUSTER_NAME[0]
            ), "Failed to migrate VM: %s with policy %s" % (
                config.MIGRATION_VM, migration_policy
            )
            time.sleep(15)


@attr(tier=2)
@pytest.mark.usefixtures(
    migration_init.__name__,
    restore_default_policy_on_vm.__name__
)
class TestVMLevelMigrationPolicies(VirtTest):
    """
    Set migration policy on VM lever and migrate VM.
    """

    __test__ = True

    @polarion("RHEVM-17042")
    def test_all_policy(self):
        """
        Set policy and migration vm
        """
        for migration_policy in config.MIGRATION_POLICY_NAME:
            testflow.step("Migrate vm with policy: %s", migration_policy)
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=config.MIGRATION_POLICY_LEGACY,
            ), "Failed to migrate VM: %s with policy %s" % (
                config.MIGRATION_VM, migration_policy
            )
        time.sleep(15)

    @polarion("RHEVM3-10444")
    def test_legacy_policy_and_optimize_features(self):
        """
        Set policy to legacy and enable auto converge and compression and
        migrate VM
        """
        testflow.step("Set policy to legacy and enable auto converge and "
                      "compression, migrate VM")
        assert migration_helper.migrate_vm_with_policy(
            migration_policy=config.MIGRATION_POLICY_LEGACY,
            auto_converge=True,
            compressed=True
        ), "Failed to migrate VM: %s with policy %s" % (
            config.MIGRATION_VM, config.MIGRATION_POLICY_LEGACY
        )
