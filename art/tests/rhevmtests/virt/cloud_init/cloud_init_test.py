#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Cloud init sanity Test
Check basic cases with cloud init
"""
import logging
import pytest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import helper
import rhevmtests.virt.helper as virt_helper
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier1,
    tier2,
)
from art.unittest_lib.common import VirtTest, testflow
from fixtures import case_setup, start_vm_with_cloud_init

logger = logging.getLogger("Cloud init VM")


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestCloudInit(VirtTest):
    """
    Cloud init test cases
    """

    __test__ = True
    vm_name = config.CLOUD_INIT_VM_NAME
    initialization = None

    @tier1
    @polarion("RHEVM3-14364")
    @pytest.mark.usefixtures(case_setup.__name__)
    @bz({"1464043": {}})
    def test_case_1_new_vm_with_cloud_init(self):
        """
        Cloud init case 1: Create new VM with cloud init parameters
        Run vm, and check configuration exists on VM
        """

        testflow.step("Start VM %s with cloud init enable", self.vm_name)
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_ip=True,
            use_cloud_init=True, wait_for_status=config.VM_UP
        )
        assert virt_helper.wait_for_vm_fqdn(self.vm_name)
        testflow.step("Check cloud init parameters")
        assert helper.check_cloud_init_parameters(
            script_content=helper.SCRIPT_CONTENT,
            time_zone=config.NEW_ZEALAND_TZ_LIST,
            hostname=config.CLOUD_INIT_HOST_NAME
        ), (
            "Failed checking VM %s, one or more of init parameter/s didn't set"
            % self.vm_name
        )

    @tier2
    @polarion("RHEVM3-4795")
    @pytest.mark.usefixtures(case_setup.__name__)
    @pytest.mark.initialization_param(user_name=config.VDC_ROOT_USER)
    def test_case_2_new_vm_with_cloud_init_run_once(self):
        """
        Cloud init case 2: Create new VM with cloud init parameters
        Run vm with run once with user root, and check configuration exists
        on VM
        """
        testflow.step("Start VM %s with cloud init enable", self.vm_name)
        logger.info("initialization parameters: %s", vars(self.initialization))
        assert ll_vms.runVmOnce(
            positive=True, vm=self.vm_name, use_cloud_init=True,
            initialization=self.initialization,
            wait_for_state=config.VM_UP
        ), "Failed to start VM %s " % self.vm_name
        assert virt_helper.wait_for_vm_fqdn(self.vm_name)
        testflow.step("Check VM %s with root user", self.vm_name)
        assert helper.check_cloud_init_parameters(
            time_zone=config.NEW_ZEALAND_TZ_LIST,
            check_nic=False, script_content=helper.SCRIPT_CONTENT,
        ), (
            "Failed checking VM %s, one or more of init parameter/s didn't set"
            % self.vm_name
        )

    @tier2
    @polarion("RHEVM3-14369")
    @pytest.mark.usefixtures(
        case_setup.__name__,
        start_vm_with_cloud_init.__name__
    )
    def test_case_3_migration_vm(self):
        """
        Cloud init case 3: Migration VM with cloud init configuration
        """
        testflow.step("Migration VM %s", self.vm_name)
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_name
        ), "Failed to migrate VM: %s " % self.vm_name
        testflow.step(
            "Check that all cloud init configuration exists after migration"
        )
        assert helper.check_cloud_init_parameters(
            script_content=helper.SCRIPT_CONTENT,
            time_zone=config.NEW_ZEALAND_TZ_LIST,
            hostname=config.CLOUD_INIT_HOST_NAME
        ), (
            "Failed checking VM %s, one or more of parameter/s didn't set" %
            self.vm_name
        )

    @tier2
    @polarion("RHEVM3-4796")
    @pytest.mark.usefixtures(case_setup.__name__)
    @pytest.mark.per_condition(set_authorized_ssh_keys=True)
    def test_case_4_authorized_ssh_keys(self):
        """
        Cloud init case 4: Check authorized ssh keys setting, connecting
        to vm without password
        """
        testflow.step("Start vm %s", self.vm_name)
        logger.info("initialization parameters: %s", vars(self.initialization))
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_ip=True,
            use_cloud_init=True, wait_for_status=config.VM_UP
        )
        assert virt_helper.wait_for_vm_fqdn(self.vm_name)
        testflow.step("Check connectivity without password")
        assert helper.check_cloud_init_parameters(
            script_content=helper.SCRIPT_CONTENT,
            time_zone=config.NEW_ZEALAND_TZ_LIST,
            hostname=config.CLOUD_INIT_HOST_NAME
        ), (
            "Failed checking VM %s, one or more of parameter/s didn't set" %
            self.vm_name
        )
