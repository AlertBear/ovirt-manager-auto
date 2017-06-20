#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import logging
import time
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import VirtTest, testflow
from rhevmtests.virt.migration.fixtures import (
    teardown_migration,
    restore_default_policy_on_cluster,
    restore_default_policy_on_vm,
    setting_migration_vm,
    load_vm
)
import config
import migration_helper

logger = logging.getLogger(__name__)


@tier2
@pytest.mark.usefixtures(
    teardown_migration.__name__,
    setting_migration_vm.__name__,
    load_vm.__name__,
    restore_default_policy_on_cluster.__name__,
)
class TestClusterLevelMigrationPoliciesAndBandwidth(VirtTest):
    """
    Update migration policy and bandwidth on cluster lever
    And migrate VM with load.
    """

    __test__ = True
    vm_name = config.MIGRATION_VM_LOAD
    load_size = 1500
    time_to_run_load = 1800

    @polarion("RHEVM-16922")
    def test_migration_with_policy_bandwidth_auto(self):
        """
        Migrate with bandwidth auto and all policies
        """
        for migration_policy in config.MIGRATION_POLICY_NAME[:4]:
            testflow.step(
                "Migrate vm with policy: %s and bandwidth: %s",
                migration_policy, config.MIGRATION_BANDWIDTH_AUTO
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                vm_name=self.vm_name,
                bandwidth_method=config.MIGRATION_BANDWIDTH_AUTO,
                cluster_name=config.CLUSTER_NAME[0]
            ), "Failed to migrate VM: %s with policy %s" % (
                self.vm_name, migration_policy
            )
            time.sleep(25)

    @polarion("RHEVM-16923")
    def test_migration_with_policy_bandwidth_hypervisor_default(self):
        """
        Migrate with bandwidth hypervisor default (52 Mbps) and all policies,
        check bandwidth with visrh domjobinfo
        """
        for migration_policy in config.MIGRATION_POLICY_NAME[:4]:
            testflow.step(
                "Migrate vm with policy: %s and bandwidth: %s, and check "
                "bandwidth",
                migration_policy, config.MIGRATION_BANDWIDTH_HYPERVISOR_DEFAULT
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                vm_name=self.vm_name,
                bandwidth_method=config.MIGRATION_BANDWIDTH_HYPERVISOR_DEFAULT,
                expected_bandwidth=config.HYPERVISOR_DEFAULT_BANDWIDTH,
                cluster_name=config.CLUSTER_NAME[0]
            ), "Failed to migrate VM: %s with policy %s" % (
                self.vm_name, migration_policy
            )
            time.sleep(25)

    @polarion("RHEVM-16924")
    def test_migration_with_policy_custom_bandwidth_32_mbps(self):
        """
        Migrate with custom bandwidth 32 Mbps and all policies,
        check bandwidth with visrh domjobinfo
        """
        for migration_policy in config.MIGRATION_POLICY_NAME[:4]:
            testflow.step(
                "Migrate vm with policy: %s and BW custom: 32 Mbps and check "
                "bandwidth", migration_policy
            )
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                vm_name=self.vm_name,
                bandwidth_method=config.MIGRATION_BANDWIDTH_CUSTOM,
                custom_bandwidth=config.CUSTOM_BW_32_MBPS,
                expected_bandwidth=config.CUSTOM_BW_32_MBPS / 2,
                cluster_name=config.CLUSTER_NAME[0],
                migration_timeout=config.MIGRATION_TIMEOUT * 2
            ), "Failed to migrate VM: %s with policy %s" % (
                self.vm_name, migration_policy
            )
            time.sleep(25)


@tier2
@pytest.mark.usefixtures(
    teardown_migration.__name__,
    setting_migration_vm.__name__,
    load_vm.__name__,
    restore_default_policy_on_vm.__name__,
)
class TestVMLevelMigrationPoliciesCase1(VirtTest):
    """
    Set migration policy on VM lever and migrate VM.
    """

    __test__ = True
    vm_name = config.MIGRATION_VM_LOAD
    load_size = 2000
    time_to_run_load = 600

    @polarion("RHEVM-17042")
    def test_all_policy(self):
        """
        Set policy on VM and migration vm
        """
        for migration_policy in config.MIGRATION_POLICY_NAME:
            testflow.step("Migrate vm with policy: %s", migration_policy)
            assert migration_helper.migrate_vm_with_policy(
                migration_policy=migration_policy,
                vm_name=self.vm_name
            ), "Failed to migrate VM: %s with policy %s" % (
                self.vm_name, migration_policy
            )
            time.sleep(25)


@tier2
@pytest.mark.usefixtures(
    teardown_migration.__name__,
    setting_migration_vm.__name__,
    load_vm.__name__,
    restore_default_policy_on_vm.__name__,
)
class TestVMLevelMigrationPoliciesCase2(VirtTest):
    """
    Legacy policy:
    Check migration with Auto Converge and XBZRLE compression enabled
    """

    __test__ = True
    vm_name = config.MIGRATION_VM_LOAD
    load_size = 2000
    time_to_run_load = 200

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
            compressed=True,
            vm_name=self.vm_name
        ), "Failed to migrate VM: %s with policy %s" % (
            config.MIGRATION_VM, config.MIGRATION_POLICY_LEGACY
        )
