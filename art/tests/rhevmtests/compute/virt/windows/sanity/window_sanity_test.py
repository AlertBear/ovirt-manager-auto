#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt Windows testing
"""

import pytest

import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.compute.virt.windows.config as config
import rhevmtests.compute.virt.windows.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier3,
)
from rhevmtests.compute.virt.windows.fixtures import (
    create_windows_vms,
    remove_vm_from_storage_domain,
    stop_vms,
    update_cluster,     # flake8: noqa
    set_product_keys,    # flake8: noqa
)
from rhevmtests.fixtures import (
    register_windows_templates,
)


@pytest.fixture(scope='module', autouse=True)  # noqa: F811
def module_setup(request,
                 register_windows_templates):
    """
    This module setup fixture imports a preconfigured
    windows SD with windows templates, attaches it and
    activates it and registers the templates.
    """
    pass


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

    @tier3
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

    @tier3
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


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(create_windows_vms.__name__)
class TestWindowsSanity02(VirtTest):
    """
    VM action testing with Windows VMs
    """

    start_vm = False

    @tier3
    @polarion("RHEVM-18239")
    @pytest.mark.usefixtures(stop_vms.__name__)
    def test_suspend_resume_windows_vm(self):
        """
        suspend and resume windows VM
        """
        for vm_name in config.WINDOWS_VM_NAMES:
            testflow.step("Suspend and resume windows VM %s", vm_name)
            assert helper.suspend_resume_vm(vm_name=vm_name)

    @tier3
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
