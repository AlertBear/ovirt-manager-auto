#! /usr/bin/python
# -*- coding: utf-8 -*-

# Test plan: RHEVM3/wiki/Compute/V2V%20automation%20cases
"""
Import VM from vmware - Negative cases
"""

import pytest
import config
import helper
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier3
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    templates as ll_templates
)
import rhevmtests.compute.virt.helper as virt_helper
from fixtures import teardown_fixture


@pytest.mark.usefixtures(teardown_fixture.__name__)
class TestNegativeImportCase1(VirtTest):
    """
    Test negative import case1: import vm which can't be imported
    """

    @tier3
    @pytest.mark.parametrize(
        ("providers", "vm_name_on_provider", "new_vm_name"),
        [
            polarion("RHEVM-24421")(
                [
                    [config.VMWARE_PROVIDER_V6],
                    config.VM_WARE_WITH_NAME_MORE_THEN_64_CHARS,
                    config.VM_WARE_WITH_NAME_MORE_THEN_64_CHARS
                ]
            ),
            polarion("RHEVM-24422")(
                [
                    [config.VMWARE_PROVIDER_V6],
                    config.VM_WARE_WITH_SNAPSHOT,
                    config.VM_WARE_WITH_SNAPSHOT
                ]
            ),
            polarion("RHEVM-24413")(
                [[config.VMWARE_PROVIDER_V6], config.VM_WARE_SPECIAL_CHARS,
                 config.VM_WARE_SPECIAL_CHARS]
            ),
        ],
        ids=[
            "Import_VM_with_name_long_then_65_chars",
            "Import_VM_with_snapshot",
            "Import_VM_with_special_characters_in_VM_name",
        ]

    )
    def test_import_vm(self, providers, vm_name_on_provider, new_vm_name):
        """
        Negative: Check that it not possible to import VM with: snapshot,
        Name longer then 65 chars

        Args:
            providers (list): vmware provider version
            vm_name_on_provider (str): VM name on vmware data center
            new_vm_name (str): New VM name on RHEVM
        """
        for provider in providers:
            testflow.step(
                "Imported vm:{p_vm} from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider, p=provider, vm=new_vm_name
                )
            )
            assert not helper.import_vm_from_external_provider(
                provider_vm_name=vm_name_on_provider,
                provider=provider,
                new_vm_name=new_vm_name,
                wait=False,
                timeout=config.TIMEOUT_IMPORT_START
            )
            test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])


@pytest.mark.usefixtures(teardown_fixture.__name__)
class TestNegativeImportCase2(VirtTest):
    """
    Test negative import case 2: Import the same vm twice
    """

    @tier3
    @pytest.mark.parametrize(
        ("providers", "vm_name_on_provider", "new_vm_name"),
        [
            polarion("RHEVM-24424")(
                [
                    [config.VMWARE_PROVIDER_V6],
                    config.VM_WARE_RHEL_7_2,
                    config.VM_WARE_RHEL_7_2
                ]
            )
        ],
        ids=[
            "Import the same vm twice"
        ]
    )
    def test_import_vm_twice(
        self, providers, vm_name_on_provider, new_vm_name
    ):
        """
        Negative: Import same VM twice

        Args:
            providers (list): vmware provider version
            vm_name_on_provider (str): VM name on vmware data center
            new_vm_name (str): New VM name on RHEVM
        """
        for provider in providers:
            testflow.step(
                "[First import] Imported vm:{p_vm} "
                "from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider,
                    p=provider,
                    vm=new_vm_name
                )
            )
            helper.import_vm_from_external_provider(
                provider_vm_name=vm_name_on_provider,
                provider=provider,
                new_vm_name=new_vm_name,
                wait=False,
                timeout=config.TIMEOUT_IMPORT_START
            )

            testflow.step(
                "[Second import] Imported vm:{p_vm} "
                "from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider,
                    p=provider,
                    vm=new_vm_name
                )
            )
            assert not helper.import_vm_from_external_provider(
                provider_vm_name=vm_name_on_provider,
                provider=provider,
                new_vm_name=new_vm_name,
                wait=False,
                timeout=config.TIMEOUT_IMPORT_START
            )
            testflow.step("Wait till first import done, and check vm")
            vm_status = ll_vms.get_vm(vm_name_on_provider).get_status_detail()
            testflow.step(
                "Waiting for event of successful import, "
                "vm status is {}".format(vm_status)
            )
            assert virt_helper.wait_for_v2v_import_event(
                vm_name=new_vm_name,
                cluster=config.IMPORT_DATA['cluster'],
                timeout=config.IMPORT_V2V_TIMEOUT
            )
            testflow.step("Check that VM status_detail is None")
            assert ll_vms.get_vm(
                vm_name_on_provider
            ).get_status_detail() is None
            assert ll_vms.get_vm(vm_name_on_provider).get_status() == 'down'
            test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])


@pytest.mark.usefixtures(teardown_fixture.__name__)
class TestNegativeImportCase3(VirtTest):
    """
    Test negative import case 3: Import vm and run actions on imported vm
    """
    description = "test_import_v2v"
    master_domain, export_domain, non_master_domain = (
        virt_helper.get_storage_domains()
    )

    @tier3
    @pytest.mark.parametrize(
        ("providers", "vm_name_on_provider", "new_vm_name"),
        [
            polarion("RHEVM-24423")(
                [
                    [config.VMWARE_PROVIDER_V6],
                    config.VM_WARE_RHEL_7_2,
                    config.VM_WARE_RHEL_7_2
                ]
            )
        ],
        ids=[
            "Import vm and run actions on imported vm"
        ]
    )
    def test_import_vm(self, providers, vm_name_on_provider, new_vm_name):
        """
        Negative:  Import VM from external provider vmware, and run actions
        On import VM - all actions should fail

        Args:
            providers (list): vmware provider version
            vm_name_on_provider (str): VM name on vmware data center
            new_vm_name (str): New VM name on RHEVM
        """
        for provider in providers:
            testflow.step(
                "Imported vm:{p_vm} from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider,
                    p=provider,
                    vm=new_vm_name
                )
            )
            helper.import_vm_from_external_provider(
                provider_vm_name=vm_name_on_provider,
                provider=provider,
                new_vm_name=new_vm_name,
                wait=False,
                timeout=config.TIMEOUT_IMPORT_START
            )
            testflow.step(
                "Run actions on imported vm, "
                "all actions should failed since vm is being imported."
            )
            assert ll_vms.startVm(positive=False, vm=vm_name_on_provider)
            assert ll_vms.removeVm(positive=False, vm=vm_name_on_provider)
            assert ll_vms.updateVm(
                positive=False,
                vm=vm_name_on_provider,
                name=self.description
            )
            assert ll_vms.addSnapshot(
                positive=False,
                vm=vm_name_on_provider,
                description=self.description
            )
            assert ll_vms.exportVm(
                positive=False,
                vm=vm_name_on_provider,
                storagedomain=self.export_domain
            )
            assert ll_templates.createTemplate(
                positive=False,
                vm=vm_name_on_provider,
                name=self.description,
                cluster=config.IMPORT_DATA["cluster"],
                storagedomain=config.IMPORT_DATA["storage_domain"]
            )
            testflow.step("Wait till import done, and check vm")
            vm_status = ll_vms.get_vm(vm_name_on_provider).get_status_detail()
            testflow.step(
                "Waiting for event of successful import, "
                "vm status is {}".format(vm_status)
            )
            assert virt_helper.wait_for_v2v_import_event(
                vm_name=new_vm_name,
                cluster=config.IMPORT_DATA['cluster'],
                timeout=config.IMPORT_V2V_TIMEOUT
            )
            testflow.step("Check that VM status_detail is None")
            assert ll_vms.get_vm(
                vm_name_on_provider
            ).get_status_detail() is None
            assert ll_vms.get_vm(vm_name_on_provider).get_status() == 'down'
