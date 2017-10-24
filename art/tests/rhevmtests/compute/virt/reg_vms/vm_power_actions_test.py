#! /usr/bin/python
# -*- coding: utf-8 -*-

# Sanity Virt: RHEVM3/wiki/Compute/Virt_VM_Sanity
# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.helpers as helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    add_vm_from_template_fixture, stateless_vm_test_fixture,
)

logger = logging.getLogger("virt_vm_base_actions")


@pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
class TestSuspendVM(VirtTest):
    __test__ = True
    base_vm_name = 'suspend_vm_test'
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    add_disk = True

    @tier1
    @polarion("RHEVM3-9962")
    def test_suspend_resume(self):
        """
        Suspend / Resume VM test
        """
        testflow.step("Check suspend/resume vm")
        assert ll_vms.startVm(
            positive=True, vm=self.base_vm_name,
            wait_for_status=config.VM_UP
        )
        testflow.step("Suspend vm %s", self.base_vm_name)
        assert ll_vms.suspendVm(True, self.base_vm_name)
        testflow.step("Resume vm %s", self.base_vm_name)
        # We use double timeout since if the storage is slow the restore
        # of the snapshot can take long time
        assert ll_vms.startVm(
            True, self.base_vm_name,
            wait_for_status=config.VM_UP,
            timeout=2 * config.VM_ACTION_TIMEOUT
        )

    @tier2
    @polarion("RHEVM3-9980")
    def test_migrate_suspend_vm(self):
        """
        Migrate suspend VM, migration should fail
        """
        testflow.step("Check migration is suspend vm")
        assert ll_vms.startVm(
            positive=True, vm=self.base_vm_name,
            wait_for_status=config.VM_UP
        )
        assert ll_vms.suspendVm(True, self.base_vm_name)
        assert not ll_vms.migrateVm(
            True, self.base_vm_name,
        ), 'succeeded migrate vm in suspend state'


@pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
class TestPauseVM(VirtTest):
    """
    VM in pause mode test cases
    """
    __test__ = True
    add_disk = True
    base_vm_name = 'pause_vm'
    vm_parameters = {'start_in_pause': True}
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]

    @tier1
    @polarion("RHEVM3-9951")
    def test_pause_vm(self):
        """
        Start vm in pause mode and check vm status
        """
        testflow.step(
            "Start vm %s in pause mode and check status", self.base_vm_name
        )
        assert ll_vms.startVm(
            True, vm=self.base_vm_name,
            wait_for_status=config.ENUMS['vm_state_paused']
        ), "Failed to start vm in pause mode"

    @tier2
    @polarion("RHEVM3-9964")
    def test_migrate_paused_vm(self):
        """
        Start vm in pause, migrate vm
        """
        testflow.step("Migrate vm in pause mode")
        assert ll_vms.startVm(
            True, vm=self.base_vm_name,
            wait_for_status=config.ENUMS['vm_state_paused']
        ), "Failed to start vm in pause mode"
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.base_vm_name,
            wait_for_status=config.VM_PAUSED
        ), "failed to migrate pause vm"


class TestStatelessVM(VirtTest):
    """
    Stateless VM tests
    """
    __test__ = True
    vm_name = "stateless_vm"
    vm_parameters = {'stateless': True}

    @tier1
    @polarion("RHEVM-14778")
    @pytest.mark.usefixtures(stateless_vm_test_fixture.__name__)
    def test_stateless_vm(self):
        """
        Create stateless vm and check vm is stateless
        """
        testflow.step("Check stateless")
        vm_obj = ll_vms.get_vm_obj(self.vm_name)
        assert vm_obj is not None, "Error finding VM %s" % self.vm_name
        stateless = vm_obj.get_stateless()
        logger.info("Actual stateless status is %s", stateless)
        assert stateless, "VM %s stateless status does not set" % self.vm_name

    @tier1
    @polarion("RHEVM3-9979")
    @pytest.mark.usefixtures(stateless_vm_test_fixture.__name__)
    def test_reboot_stateless_vm(self):
        """
        1. Create stateless vm
        2. Create file on VM
        3. Reboot VM
        4. Check that after reboot file don't exists
        """
        testflow.step("Check stateless vm reboot")
        vm_resource = helper.get_vm_resource(self.vm_name)
        testflow.step("Create file on vm")
        virt_helper.create_file_in_vm(
            vm=self.vm_name, vm_resource=vm_resource
        )
        assert vm_resource.run_command(['sync'])[0] == 0
        testflow.step("Reboot vm, and check that file don't exist")
        virt_helper.reboot_stateless_vm(self.vm_name)
        assert not virt_helper.check_if_file_exist(
            positive=False, vm=self.vm_name, vm_resource=vm_resource
        ), "File exists after reboot vm "
