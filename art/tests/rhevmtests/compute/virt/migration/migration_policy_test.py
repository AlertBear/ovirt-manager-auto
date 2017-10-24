#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import time

import pytest

import config
import migration_helper
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import tier2
from fixtures import (
    teardown_migration,
    restore_default_policy_on_cluster,
    restore_default_policy_on_vm,
    setting_migration_vm,
    load_vm
)


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

    vm_name = config.MIGRATION_VM_LOAD
    load_size = 1500
    time_to_run_load = 1800

    @tier2
    @pytest.mark.parametrize(
        ('bandwidth', 'expected_bw'),
        [
            pytest.param(
                (config.BW_AUTO, None),
                None,
                marks=(polarion("RHEVM-16922")),
                id=config.BW_AUTO
            ),

            pytest.param(
                (config.BW_HYPERVISOR_DEFAULT, config.HYPERVISOR_DEFAULT_BW),
                config.HYPERVISOR_DEFAULT_BW,
                marks=(polarion("RHEVM-16923")),
                id=config.BW_HYPERVISOR_DEFAULT
            ),
            pytest.param(
                (config.BW_CUSTOM, config.CUSTOM_BW_32_MBPS),
                config.CUSTOM_BW_32_MBPS / 2,
                marks=(polarion("RHEVM-16924")),
                id=config.BW_CUSTOM
            ),
        ]
    )
    @pytest.mark.parametrize(
        'migration_policy',
        config.MIGRATION_POLICY_NAMES,
        ids=config.MIGRATION_POLICY_NAMES
    )
    def test_migration_policy(self, migration_policy, bandwidth, expected_bw):
        """
        Migrate with all bandwidth and all policies
        """
        if migration_policy == config.BW_CUSTOM:
            testflow.step('Restart VM to remove load process')
            ll_vms.restartVm(vm=self.vm_name)
        testflow.step(
            "Migrate vm with policy: %s and bandwidth: %s",
            migration_policy, config.BW_AUTO
        )
        assert migration_helper.migrate_vm_with_policy(
            migration_policy=migration_policy,
            vm_name=self.vm_name,
            bandwidth_method=bandwidth[0],
            custom_bandwidth=bandwidth[1],
            expected_bandwidth=expected_bw,
            cluster_name=config.CLUSTER_NAME[0]
        ), "Failed to migrate VM: %s with policy %s" % (
            self.vm_name, migration_policy
        )
        # This is added to handle the case when VM is migrated, but is still
        #  reported on the source host
        time.sleep(config.ENGINE_STAT_UPDATE_INTERVAL)


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

    vm_name = config.MIGRATION_VM_LOAD
    load_size = 2000
    time_to_run_load = 600

    @tier2
    @polarion("RHEVM-17042")
    @pytest.mark.parametrize(
        'migration_policy',
        config.MIGRATION_POLICY_NAMES,
        ids=config.MIGRATION_POLICY_NAMES
    )
    def test_all_policy(self, migration_policy):
        """
        Set policy on VM and migration vm
        """
        testflow.step("Migrate vm with policy: %s", migration_policy)
        assert migration_helper.migrate_vm_with_policy(
            migration_policy=migration_policy,
            vm_name=self.vm_name
        ), "Failed to migrate VM: %s with policy %s" % (
            self.vm_name, migration_policy
        )
        # This is added to handle the case when VM is migrated, but is still
        #  reported on the source host
        time.sleep(config.ENGINE_STAT_UPDATE_INTERVAL)


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

    vm_name = config.MIGRATION_VM_LOAD
    load_size = 2000
    time_to_run_load = 200

    @tier2
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
