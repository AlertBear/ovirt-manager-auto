#! /usr/bin/python
# -*- coding: utf-8 -*-

# Sanity Virt: RHEVM3/wiki/Compute/Virt_VM_Sanity
# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

import logging
import time
import pytest
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, VirtTest, testflow
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.helpers as helper
import rhevmtests.virt.helper as virt_helper
from art.rhevm_api.utils import test_utils
from rhevmtests.virt.reg_vms.fixtures import (
    add_vm_from_template_fixture, stateless_vm_test_fixture,
)
import config

logger = logging.getLogger("virt_vm_base_actions")


@pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
class TestPowerActions(VirtTest):
    __test__ = True
    vm_name = 'power_actions'
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    add_disk = False
    vm_parameters = None

    @attr(tier=2)
    @polarion("RHEVM3-12587")
    def test_locked_vm(self):
        """
        Change vm status in database to locked and try to remove it
        """
        testflow.step("remove locked vm")
        test_utils.update_vm_status_in_database(
            self.vm_name,
            vdc=config.VDC_HOST,
            status=int(config.ENUMS['vm_status_locked_db']),
            vdc_pass=config.VDC_ROOT_PASSWORD
        )
        test_utils.wait_for_tasks(
            config.VDC_HOST, config.VDC_ROOT_PASSWORD,
            config.DC_NAME[0]
        )
        time.sleep(20)
        assert ll_vms.remove_locked_vm(
            self.vm_name,
            vdc=config.VDC_HOST,
            vdc_pass=config.VDC_ROOT_PASSWORD
        )

    @attr(tier=1)
    @bz({"1389996": {}})
    @polarion("RHEVM3-9962")
    def test_suspend_resume(self):
        """
        Suspend / Resume VM test
        """
        testflow.step("Check suspend/resume vm")
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name,
            wait_for_status=config.VM_UP
        )
        testflow.step("Suspend vm %s", self.vm_name)
        assert ll_vms.suspendVm(True, self.vm_name)
        testflow.step("Resume vm %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name,
            wait_for_status=config.VM_UP
        )

    @attr(tier=2)
    @polarion("RHEVM3-9980")
    def test_migrate_suspend_vm(self):
        """
        Migrate suspend VM, migration should fail
        """
        testflow.step("Check migration is suspend vm")
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name,
            wait_for_status=config.VM_UP
        )
        assert ll_vms.suspendVm(True, self.vm_name)
        assert not ll_vms.migrateVm(
            True, self.vm_name,
        ), 'succeeded migrate vm in suspend state'


@attr(tier=1)
@pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
class TestPauseVM(VirtTest):
    """
    VM in pause mode test cases
    """
    __test__ = True
    vm_name = 'pause_vm'
    vm_parameters = {'start_in_pause': True}
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]

    @polarion("RHEVM3-9951")
    def test_pause_vm(self):
        """
        Start vm in pause mode and check vm status
        """
        testflow.step(
            "Start vm %s in pause mode and check status", self.vm_name
        )
        assert ll_vms.startVm(
            True, vm=self.vm_name,
            wait_for_status=config.ENUMS['vm_state_paused']
        ), "Failed to start vm in pause mode"

    @attr(tier=1)
    @polarion("RHEVM3-9964")
    @bz({"1273720": {}})
    def test_migrate_paused_vm(self):
        """
        Negative:
        Start vm in pause, migrate vm
        """
        testflow.step("Migrate vm in pause mode")
        assert ll_vms.startVm(
            True, vm=self.vm_name,
            wait_for_status=config.ENUMS['vm_state_paused']
        ), "Failed to start vm in pause mode"
        host_before = ll_vms.get_vm_host(self.vm_name)
        # set time to '0', need only to check if vm is up since it in pause
        # mode
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_name, timeout=0
        ), "pause vm has migrate"
        host_after = ll_vms.get_vm_host(self.vm_name)
        assert host_before != host_after, "vm did stay on the same host"


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestStatelessVM(VirtTest):
    """
    Stateless VM tests
    """
    __test__ = True
    vm_name = "stateless_vm"
    vm_parameters = {'stateless': True}

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
