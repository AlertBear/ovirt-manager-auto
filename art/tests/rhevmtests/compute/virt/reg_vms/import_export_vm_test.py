#! /usr/bin/python
# -*- coding: utf-8 -*-

# Sanity Virt: RHEVM3/wiki/Compute/Virt_VM_Sanity
# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

"""
Import Export VM test
"""

import logging

import pytest

import art.test_handler.exceptions as errors
import config
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier1,
)
from rhevmtests.compute.virt import helper
from fixtures import (
    test_snapshot_and_import_export_fixture,
)

logger = logging.getLogger("import_export_vm")


class ImportExportVm(VirtTest):
    """
    Check different cases for import/export vm
    """
    __test__ = True
    vm_name = 'virt_export_vm'
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @tier1
    @polarion("RHEVM3-12525")
    @pytest.mark.usefixtures(test_snapshot_and_import_export_fixture.__name__)
    def test_basic_import_export_vm(self):
        """
        Basic: Import Export test
            1) Export vm
            2) Export vm, that override existing one
            3) Import exported vm
            4) Negative: import existed vm
        """
        testflow.step("Export vm %s", self.vm_name)
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)

        testflow.step(
            "Export vm %s, that override existing one", self.vm_name
        )
        assert ll_vms.exportVm(
            positive=True,
            vm=self.vm_name,
            storagedomain=self.export_domain,
            exclusive='true'
        )
        testflow.step("Remove vm %s", self.vm_name)
        if not ll_vms.removeVm(True, self.vm_name):
            raise errors.VMException("Failed to remove vm")
        logger.info("Import exported vm %s", self.vm_name)
        assert ll_vms.importVm(
            True,
            self.vm_name,
            self.export_domain,
            self.master_domain,
            config.CLUSTER_NAME[0]
        )
        testflow.step("Negative: Import existed vm")
        assert not ll_vms.importVm(
            True,
            self.vm_name,
            self.export_domain,
            self.master_domain,
            config.CLUSTER_NAME[0]
        )
