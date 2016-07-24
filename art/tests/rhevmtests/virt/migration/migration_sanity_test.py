#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt sanity testing for migration feature.
"""

import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import attr, VirtTest, testflow
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib.network as network_lib
from rhevmtests.virt.migration.fixtures import (
    cancel_migration_test, migration_init, restart_vm
)
import config


@attr(tier=1)
@pytest.mark.usefixtures(
    migration_init.__name__,
    restart_vm.__name__
)
class TestMigrationVirtSanityCase1(VirtTest):
    """
    Virt Migration sanity case:
    Check migration of one VM
    """

    __test__ = True

    @polarion("RHEVM3-3847")
    def test_migration(self):
        testflow.step("Check migration of one VM")
        assert ll_vms.migrateVm(
            positive=True,
            vm=config.MIGRATION_VM
        ), "Failed to migrate VM: %s " % config.MIGRATION_VM


@attr(tier=1)
@pytest.mark.usefixtures(
    migration_init.__name__
)
class TestMigrationVirtSanityCase2(VirtTest):
    """
    Virt Migration sanity case:
    Check maintenance on SPM host with one VM
     """
    __test__ = True

    @polarion("RHEVM3-12332")
    def test_maintenance_of_spm(self):
        testflow.step("Check maintenance on SPM host with one VM")
        assert hl_vms.migrate_by_maintenance(
            vms_list=[config.MIGRATION_VM],
            src_host=network_lib.get_host(config.MIGRATION_VM),
            vm_os_type=config.RHEL_OS_TYPE_FOR_MIGRATION,
            vm_user=config.VMS_LINUX_USER,
            vm_password=config.VMS_LINUX_PW,
            connectivity_check=config.CONNECTIVITY_CHECK
        ), "Maintenance test failed"


@attr(tier=1)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    migration_init.__name__,
    cancel_migration_test.__name__
)
class TestMigrationVirtSanityCase3(VirtTest):
    """
    Check cancel VM migration.
    1. Start migrate vm in different thread
    2. Cancel migration
    3. Check the cancel succeed (VM stay on the source host)
    """
    __test__ = True

    @polarion("RHEVM3-14032")
    def test_cancel_migration(self):
        testflow.step("Migrate VM %s", config.MIGRATION_VM)
        assert ll_vms.migrateVm(
            positive=True,
            vm=config.MIGRATION_VM,
            wait=False
        )
        ll_vms.wait_for_vm_states(
            vm_name=config.MIGRATION_VM,
            states=[
                config.ENUMS['vm_state_migrating'],
                config.ENUMS['vm_state_migrating_from'],
                config.ENUMS['vm_state_migrating_to']
            ]
        )
        testflow.step("Cancel VM %s migration ", config.MIGRATION_VM)
        config.CANCEL_VM_MIGRATE = hl_vms.cancel_vm_migrate(
            vm=config.MIGRATION_VM,
        )
        assert config.CANCEL_VM_MIGRATE, (
            "Cancel migration didn't succeed for VM:%s " % config.MIGRATION_VM
        )
