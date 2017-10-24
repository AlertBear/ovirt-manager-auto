#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: /RHEVM3/wiki/Compute/3_5_VIRT_Clone_VM

import logging
import time

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as virt_helper
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
)
from fixtures import (
    add_vm_fixture,
    add_vm_from_template_fixture,
    basic_teardown_fixture,
    create_vm_and_template_with_small_disk,
    start_stop_fixture,
    create_file_on_vm,
    add_vm_with_disks,
    remove_locked_vm,
    unlock_disks,
)

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    create_vm_and_template_with_small_disk.__name__,
    basic_teardown_fixture.__name__,
)
class CloneVMSanityTestCase1(VirtTest):
    __test__ = True
    vm_name = config.CLONE_VM_TEST
    vm_parameters = config.CLONE_VM_TEST_VM_PARAMETERS

    @tier1
    @polarion("RHEVM3-12582")
    def test_clone_vm_template_case(self):
        """
        Clone vm directly from template
        """
        testflow.step(
            "Clone vm %s directly from template %s",
            self.vm_name, config.BASE_TEMPLATE
        )
        assert ll_vms.cloneVmFromTemplate(
            positive=True,
            name=self.vm_name,
            template=config.BASE_TEMPLATE,
            cluster=config.CLUSTER_NAME[0],
        )


@pytest.mark.usefixtures(
    add_vm_from_template_fixture.__name__,
    create_file_on_vm.__name__,
    basic_teardown_fixture.__name__,
)
class CloneVMSanityTestCase2(VirtTest):
    __test__ = True
    base_vm_name = config.VM_FROM_BASE_TEMPLATE
    clone_vm = config.CLONE_VM_TEST
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    vm_parameters = config.CLONE_VM_TEST_VM_PARAMETERS

    @tier2
    @polarion("RHEVM3-6511")
    def test_clone_vm(self):
        """
        Create VM from template and clone vm.
        """
        testflow.setup("Create VM from template and clone vm.")
        assert hl_vms.clone_vm(
            positive=True, vm=config.VM_FROM_BASE_TEMPLATE,
            clone_vm_name=config.CLONE_VM_TEST
        )
        assert virt_helper.check_clone_vm(
            clone_vm_name=config.CLONE_VM_TEST,
            base_vm_name=config.VM_FROM_BASE_TEMPLATE,
        )
        virt_helper.check_disk_contents_on_clone_vm(
            clone_vm_name=config.CLONE_VM_TEST
        )


@pytest.mark.usefixtures(
    add_vm_fixture.__name__,
    basic_teardown_fixture.__name__,
)
class CloneVMSanityTestCase3(VirtTest):
    __test__ = True
    vm_name = config.BASE_VM_VIRT
    add_disk = False

    @tier2
    @polarion("RHEVM3-6509")
    def test_clone_vm_without_disks(self):
        """
        Clone VM without disks
        """
        testflow.step("Clone VM without disk/s")
        assert hl_vms.clone_vm(
            positive=True, vm=self.vm_name,
            clone_vm_name=config.TEST_CLONE_WITH_WITHOUT_DISKS,
            wait=False
        )


@pytest.mark.usefixtures(
    basic_teardown_fixture.__name__,
    add_vm_with_disks.__name__,
    basic_teardown_fixture.__name__,
)
class CloneVmDisksCase(VirtTest):
    """
    Clone VM with disks on master domain
    """
    __test__ = True
    vm_name = config.BASE_VM_VIRT

    @tier2
    @polarion("RHEVM3-6521")
    def test_clone_vm_with_disks_on_master(self):
        testflow.step("Clone VM with disks on master domain")
        assert hl_vms.clone_vm(
            positive=True, vm=self.vm_name,
            clone_vm_name=config.TEST_CLONE_WITH_2_DISKS
        )
        assert virt_helper.check_clone_vm(
            clone_vm_name=config.TEST_CLONE_WITH_2_DISKS,
            base_vm_name=self.vm_name,
        )


@pytest.mark.usefixtures(
    add_vm_from_template_fixture.__name__,
    start_stop_fixture.__name__
)
class CloneVmNegativeCase1(VirtTest):
    """
    Clone negatives: Clone VM which is up and running
    """
    __test__ = True
    base_vm_name = config.BASE_VM_VIRT
    clone_vm = config.CLONE_VM_TEST
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]

    @tier3
    @polarion("RHEVM-17353")
    def test_negative_running_vm(self):
        testflow.step("Clone VM which is up and running")
        assert not hl_vms.clone_vm(
            positive=False, vm=self.base_vm_name,
            clone_vm_name=config.CLONE_VM_TEST, wait=False
        )


@pytest.mark.usefixtures(
    add_vm_from_template_fixture.__name__,
)
class CloneVmNegativeCase2(VirtTest):
    """
    Clone negative: Clone VM which is in pause state
    """
    __test__ = True
    base_vm_name = config.BASE_VM_VIRT
    clone_vm = config.CLONE_VM_TEST
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    vm_parameters = {'start_in_pause': True}

    @tier3
    @polarion("RHEVM-17355")
    def test_negative_paused_vm(self):
        """
        Clone VM which is in pause state
        """
        testflow.step("Start VM in pause state")
        assert ll_vms.startVm(
            True, vm=self.base_vm_name,
            wait_for_status=config.ENUMS['vm_state_paused']
        ), "Failed to start vm in pause mode"
        testflow.step("Clone VM which is in pause state")
        assert not hl_vms.clone_vm(
            positive=False, vm=self.base_vm_name,
            clone_vm_name=config.CLONE_VM_TEST, wait=False
        )


@pytest.mark.usefixtures(
    add_vm_from_template_fixture.__name__,
    remove_locked_vm.__name__
)
class CloneVmNegativeCase3(VirtTest):
    """
    Clone negative: Clone vm in locked state
    """
    __test__ = True
    base_vm_name = config.BASE_VM_VIRT
    clone_vm = config.CLONE_VM_TEST
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]

    @tier3
    @polarion("RHEVM-17354")
    def test_negative_locked_vm(self):
        testflow.step("lock VM in DB")
        test_utils.update_vm_status_in_database(
            vm_name=self.base_vm_name,
            vdc=config.VDC_HOST,
            status=int(config.ENUMS['vm_status_locked_db']),
            vdc_pass=config.VDC_ROOT_PASSWORD
        )
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        time.sleep(20)
        testflow.step("clone vm in locked state")
        assert not hl_vms.clone_vm(
            positive=False, vm=config.BASE_VM_VIRT,
            clone_vm_name=config.CLONE_VM_TEST, wait=False
        )


@pytest.mark.usefixtures(
    add_vm_from_template_fixture.__name__,
    unlock_disks.__name__,
)
class CloneVmNegativeCase4(VirtTest):
    """
    Clone negative: Clone same VM twice at the same time
    """
    __test__ = True
    base_vm_name = config.BASE_VM_VIRT
    clone_vm = config.CLONE_VM_TEST
    clone_vm_twice = 'clone_same_vm_twice'
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]

    @tier3
    @polarion("RHEVM3-6509")
    def test_negative_same_vm_parallel(self):
        testflow.step("Clone negative: Clone same VM twice at the same time")
        testflow.step("First clone")
        assert hl_vms.clone_vm(
            positive=True, vm=self.base_vm_name,
            clone_vm_name=config.CLONE_VM_TEST, wait=False
        )
        time.sleep(5)
        testflow.step("Second clone")
        assert not hl_vms.clone_vm(
            positive=False, vm=self.base_vm_name,
            clone_vm_name=self.clone_vm_twice, wait=False
        )
