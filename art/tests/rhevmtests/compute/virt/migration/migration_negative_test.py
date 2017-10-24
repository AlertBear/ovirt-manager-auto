#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Negative Migration Test - Tests to check vm migration
"""

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier3,
)
from fixtures import (
    migrate_to_diff_dc, over_load_test,
    migration_options_test, migration_init,
)


@pytest.mark.skipif(
    config.NO_HYPERCONVERGED_SUPPORT,
    reason=config.NO_HYPERCONVERGED_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(
    migration_init.__name__,
    migrate_to_diff_dc.__name__
)
class TestMigrateNegativeCase1(VirtTest):
    """
    Negative cases:
        1. No available host on cluster
        2. Migrate vm to other data center
    """
    __test__ = True

    @tier3
    @polarion("RHEVM3-5666")
    def test_migrate_no_available_host_on_cluster(self):
        testflow.step(
            "Negative step: Migration to no available host on cluster"
        )
        assert ll_vms.migrateVm(
            positive=False,
            vm=config.MIGRATION_VM
        ), 'migration success although'
        'no available host on cluster'

    @tier3
    @polarion("RHEVM3-5658")
    def test_migrate_vm_to_other_data_center(self):
        testflow.step("Negative step: Migrate vm to another data center")
        assert ll_vms.migrateVm(
            positive=False,
            vm=config.MIGRATION_VM,
            host=config.HOSTS[1]
        ), 'migration success although'
        'migration between data centers is not supported'


@pytest.mark.usefixtures(
    migration_init.__name__
)
class TestMigrateNegativeCase2(VirtTest):
    """
    Negative: Migrate vm on the same host
    """
    __test__ = True

    @tier3
    @polarion("RHEVM3-5657")
    def test_migrate_vm_on_same_host(self):
        host = ll_vms.get_vm_host(config.MIGRATION_VM)
        testflow.step("Negative step: Migrate vm on the same host")
        assert ll_vms.migrateVm(
            positive=False,
            vm=config.MIGRATION_VM,
            host=host
        ), 'migration success although'
        'migration to the same host is NOT supported'


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    migration_init.__name__,
    over_load_test.__name__
)
class TestMigrateNegativeCase3(VirtTest):
    """
    Negative: Migrate vm to overload host
    """
    __test__ = True
    test_vms = config.VM_NAME[1:3]

    @tier3
    @polarion("RHEVM3-5656")
    def test_migration_overload_host(self):
        testflow.step(
            "Set the host %s (with the large memory) to maintenance",
            config.HOSTS[config.HOST_INDEX_MAX_MEMORY]
        )
        expected_host_status = config.ENUMS[
            'host_state_preparing_for_maintenance'
        ]
        assert ll_hosts.deactivate_host(
            positive=True,
            host=config.HOSTS[config.HOST_INDEX_MAX_MEMORY],
            expected_status=expected_host_status
        ), "Failed to deactivate host"
        testflow.step("Check that all vms still in up state")
        assert ll_vms.waitForVmsStates(
            positive=True,
            names=self.test_vms
        ), "not all VMs are up"


@pytest.mark.usefixtures(
    migration_init.__name__,
    migration_options_test.__name__
)
class TestVMMigrateOptions(VirtTest):
    """
    Negative case: VM Migration options case
    Create new VM with migration options disable (pin to host)
    """
    __test__ = True
    vm_name = 'DoNotAllowMigration'

    @tier3
    @polarion("RHEVM3-5625")
    def test_migration_new_vm(self):
        """
         Negative test:
         Migration new VM with option 'Do not allow migration'
        """
        assert ll_vms.migrateVm(
            positive=False,
            vm=self.vm_name,
            host=config.HOSTS[1]
        ), 'Migration succeed although vm set to "Do not allow migration"'
