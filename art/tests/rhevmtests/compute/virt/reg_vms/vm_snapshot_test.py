#! /usr/bin/python
# -*- coding: utf-8 -*-

# Sanity Virt: RHEVM3/wiki/Compute/Virt_VM_Sanity
# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.virt.helper as helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    test_snapshot_and_import_export_fixture
)

logger = logging.getLogger("virt_snapshot_test")
VM_REMOVE_SNAPSHOT_TIMEOUT = 4000


class VmSnapshots(VirtTest):
    """
    Create, restore and remove vm snapshots
    """
    __test__ = True
    vm_name = 'snapshot_vm'
    snapshot_description = ['snapshot_1', 'snapshot_2']
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @tier1
    @polarion("RHEVM3-10089")
    @pytest.mark.usefixtures(test_snapshot_and_import_export_fixture.__name__)
    def test_basic_vm_snapshots(self):
        """
        Create, restore, export and remove snapshots
        """
        testflow.step(
            "Create two new snapshots of vm %s", self.vm_name
        )
        for description in self.snapshot_description:
            job_description = "Creating VM Snapshot %s for VM %s" % (
                description, self.vm_name
            )
            logger.info("add snapshot job description: %s", job_description)
            assert ll_vms.addSnapshot(
                positive=True,
                vm=self.vm_name,
                description=description,
            ), "Failed to add snapshot to VM."
        testflow.step(
            "Restore vm %s from snapshot %s",
            self.vm_name,
            self.snapshot_description[1]
        )
        assert ll_vms.restore_snapshot(
            True,
            self.vm_name,
            self.snapshot_description[1]
        )
        testflow.step("Export vm %s with discarded snapshots", self.vm_name)
        assert ll_vms.exportVm(
            positive=True,
            vm=self.vm_name,
            storagedomain=self.export_domain,
            discard_snapshots='true'
        )
        testflow.step(
            "Remove snapshots %s and %s of vm %s",
            self.snapshot_description[0],
            self.snapshot_description[1],
            self.vm_name
        )
        for snapshot in self.snapshot_description:
            assert ll_vms.removeSnapshot(
                positive=True,
                vm=self.vm_name,
                description=snapshot,
                timeout=VM_REMOVE_SNAPSHOT_TIMEOUT
            )

    @tier2
    @polarion("RHEVM3-12581")
    @pytest.mark.usefixtures(test_snapshot_and_import_export_fixture.__name__)
    def test_basic_vm_snapshots_with_memory(self):
        """
        Create, restore, export and remove snapshots
        """
        assert ll_vms.startVm(True, self.vm_name)
        testflow.step(
            "Create two new snapshots of vm %s with memory",
            self.vm_name
        )
        for description in self.snapshot_description:
            job_description = (
                "Creating VM Snapshot %s with memory from VM %s" %
                (description, self.vm_name)
            )
            logger.info("add snapshot job description: %s", job_description)
            assert ll_vms.addSnapshot(
                positive=True,
                vm=self.vm_name,
                description=description,
                persist_memory=True,
            ), "Failed to add snapshot to VM."
        testflow.step(
            "Restore vm %s from snapshot %s",
            self.vm_name,
            self.snapshot_description[1]
        )
        assert ll_vms.restore_snapshot(
            True,
            self.vm_name,
            self.snapshot_description[1],
            restore_memory=True,
            ensure_vm_down=True
        )
        testflow.step(
            "Remove snapshots %s and %s of vm %s",
            self.snapshot_description[0],
            self.snapshot_description[1],
            self.vm_name
        )
        for snapshot in self.snapshot_description:
            assert ll_vms.removeSnapshot(
                positive=True,
                vm=self.vm_name,
                description=snapshot,
                timeout=VM_REMOVE_SNAPSHOT_TIMEOUT
            )
