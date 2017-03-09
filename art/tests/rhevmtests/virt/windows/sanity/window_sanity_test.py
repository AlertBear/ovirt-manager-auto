#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt Windows testing
"""

import pytest
from art.unittest_lib import attr, VirtTest, testflow
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
import rhevmtests.virt.helper as virt_helper
import rhevmtests.virt.windows.config as config
import rhevmtests.virt.windows.helper as helper
from rhevmtests.virt.windows.fixtures import (
    create_windows_vms,
    remove_vm_from_storage_domain,
    stop_vms,
    update_cluster,     # flake8: noqa
    set_product_keys,    # flake8: noqa
)


@attr(tier=3)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    create_windows_vms.__name__, remove_vm_from_storage_domain.__name__
)
class TestWindowsSanity01(VirtTest):
    """
    Case 1: Migrate Windows VM test
    Case 2: Snapshot test
    """
    master_domain, export_domain, non_master_domain = (
        virt_helper.get_storage_domains()
    )

    @polarion("RHEVM-18238")
    def test_1_migrate_windows_vms(self):
        """
        Check migration for all windows VMs
        """
        testflow.setup("Migrate test for all Windows types")
        assert virt_helper.job_runner(
            job_name="migration",
            kwargs_info=helper.migrate_job_info(),
            job_method_name=ll_vms.migrateVm,
            vms_list=config.WINDOWS_VM_NAMES
        )

    @polarion("RHEVM-18235")
    def test_2_vm_snapshots_with_memory(self):
        """
        Create, restore, export and remove snapshots with memory
        """
        testflow.setup("Snapshots with memory")
        helper.wait_for_snapshot_jobs(
            vms_list=config.WINDOWS_VM_NAMES,
            export_domain=self.export_domain,
            with_memory=True
        )


@attr(tier=3)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(create_windows_vms.__name__)
class TestWindowsSanity02(VirtTest):
    """
    VM action testing with Windows VMs
    """

    start_vm = False

    @polarion("RHEVM-18239")
    @pytest.mark.usefixtures(stop_vms.__name__)
    def test_suspend_resume_windows_vm(self):
        """
        suspend and resume windows VM
        """
        for vm_name in config.WINDOWS_VM_NAMES:
            testflow.step("Suspend and resume windows VM %s", vm_name)
            assert helper.suspend_resume_vm(vm_name=vm_name)

    @polarion("RHEVM-18240")
    @pytest.mark.usefixtures(stop_vms.__name__)
    def test_pause_windows_vm(self):
        """
        Start vm in pause mode and check vm status
        """
        for vm_name in config.WINDOWS_VM_NAMES:
            testflow.step(
                "Start vm %s in pause mode and check status", vm_name
            )
            assert ll_vms.startVm(
                True, vm=vm_name,
                pause=True
            ), "Failed to start vm in pause mode"
