#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt sanity testing for migration feature.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
)
from fixtures import (
    migration_init, start_vm_on_spm
)


@pytest.mark.usefixtures(
    migration_init.__name__,
)
class TestMigrationVirtSanityCase1(VirtTest):
    """
    Virt Migration sanity case:
    Check migration of one VM
    """

    __test__ = True

    @tier1
    @polarion("RHEVM3-3847")
    def test_migration(self):
        testflow.step("Check migration of one VM")
        assert ll_vms.migrateVm(
            positive=True,
            vm=config.MIGRATION_VM
        ), "Failed to migrate VM: %s " % config.MIGRATION_VM


@pytest.mark.usefixtures(
    migration_init.__name__,
    start_vm_on_spm.__name__
)
class TestMigrationVirtSanityCase2(VirtTest):
    """
    Virt Migration sanity case:
    Check maintenance on SPM host with one VM
     """
    __test__ = True

    @tier1
    @polarion("RHEVM3-12332")
    def test_maintenance_of_spm(self):
        testflow.step("Check maintenance on SPM host with one VM")
        vm_host = ll_vms.get_vm_host(vm_name=config.MIGRATION_VM)
        assert vm_host, "Failed to get VM: %s hoster" % config.MIGRATION_VM
        assert hl_vms.migrate_by_maintenance(
            vms_list=[config.MIGRATION_VM],
            src_host=vm_host,
            vm_os_type=config.RHEL_OS_TYPE_FOR_MIGRATION,
            vm_user=config.VMS_LINUX_USER,
            vm_password=config.VMS_LINUX_PW,
            connectivity_check=config.CONNECTIVITY_CHECK
        ), "Maintenance test failed"
