#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import logging

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as virt_helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier2,
    tier3,
)
from fixtures import (
    migration_init,
    start_vms_on_specific_host,
    setting_migration_vm,
    migration_with_two_disks,
    cancel_migration_test,
    load_vm,
    teardown_migration
)

logger = logging.getLogger("virt_migration_mix_cases")


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

    @tier3
    @polarion("RHEVM3-5646")
    def test_bidirectional_migration_between_two_hosts(self):
        testflow.step("Test bidirectional vms migration between two hosts")
        assert virt_helper.migration_vms_to_diff_hosts(
            vms=config.VM_NAME[1:5]
        ), "Failed to migration all VMs"


@pytest.mark.usefixtures(
    migration_init.__name__,
    migration_with_two_disks.__name__
)
class TestMigrationMixCase2(VirtTest):
    """
    1. Add to VM 2 disks and migrate VM
    2. Remove disks in the end
    """
    __test__ = True
    vm_name = "VM_with_2_disks"

    @tier3
    @polarion("RHEVM3-5647")
    def test_migrate_vm_with_more_then_one_disk(self):
        testflow.step("Migrate VM with more then one disk")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name,
            wait=True
        ), "Failed to migrate VM with more then 1 disk"


@pytest.mark.usefixtures(migration_init.__name__)
class TestMigrationMixCase3(VirtTest):
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

    @tier3
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


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    cancel_migration_test.__name__,
    setting_migration_vm.__name__,
    load_vm.__name__,
    teardown_migration.__name__
)
class TestCancelMigration(VirtTest):
    """
    Check cancel VM migration.
    1. Start migrate vm with load in different thread
    2. Cancel migration
    3. Check the cancel succeed (VM stay on the source host)
    """
    __test__ = True
    vm_name = config.MIGRATION_VM_LOAD
    load_size = 2000
    time_to_run_load = 120

    @tier2
    @polarion("RHEVM3-14032")
    def test_cancel_migration(self):
        testflow.step("Migrate VM %s", self.vm_name)
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name,
            wait=False
        )
        ll_vms.wait_for_vm_states(
            vm_name=self.vm_name,
            states=[
                config.ENUMS['vm_state_migrating'],
                config.ENUMS['vm_state_migrating_from'],
                config.ENUMS['vm_state_migrating_to']
            ]
        )
        testflow.step("Cancel VM %s migration ", self.vm_name)
        config.CANCEL_VM_MIGRATE = hl_vms.cancel_vm_migrate(
            vm=self.vm_name,
        )

        assert config.CANCEL_VM_MIGRATE, (
            "Cancel migration didn't succeed for VM:%s " % config.MIGRATION_VM
        )
