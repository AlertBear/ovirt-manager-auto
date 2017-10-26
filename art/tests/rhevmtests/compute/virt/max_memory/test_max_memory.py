#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: /RHEVM3/wiki/Compute/Virt_VMs

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
import rhevmtests.compute.virt.helper as helper
import rhevmtests.compute.virt.hot_plug_unplug.memory_hotplug.helper as \
    mh_helper
import rhevmtests.helpers as global_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools
)
from art.test_handler.tools import polarion, bz
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from rhevmtests.compute.virt.fixtures import (
    create_vm, create_vm_pool, remove_created_vms
)


@pytest.mark.usefixtures(create_vm.__name__, remove_created_vms.__name__)
class TestMaxMemory(VirtTest):
    """
    Check VM maximum memory tests
    """
    reg_vms = config.REG_VMS_LIST
    vm_parameters = config.VM_PARAMETERS
    vm_name = vm_parameters['name']

    @polarion("RHEVM-19329")
    @tier1
    def test_new_vm_update_max_memory(self):
        """
        Positive: Add default vm and check its maximum memory
        """
        testflow.step("Positive: Get vm with name: {vm_name}".format(
            vm_name=self.vm_name))
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        assert ll_vms.runVmOnce(True, vm.name, wait_for_state='up')
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO

    @pytest.mark.parametrize(
        "memory_to_expand", [
            polarion("RHEVM-19317")(config.GB),
            polarion("RHEVM-19333")(config.VM_MEMORY * 3)
        ],
        ids=[
            "hotplug_1GB",
            "hotplug_up_to_maximum"
        ]
    )
    @tier2
    def test_hotplug_max_memory(self, memory_to_expand):
        """
        Positive: Add default vm, hotplug memory, check max memory
        """
        vm = ll_vms.get_vm(self.vm_name)
        memory_before = vm.memory
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        assert ll_vms.runVmOnce(True, vm.name, wait_for_state='up')
        testflow.step("Positive: Hotplug RAM to VM and check memory")
        assert mh_helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=memory_to_expand
        )
        assert hl_vms.reboot_to_state(vm=self.vm_name)
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory == memory_before + memory_to_expand
        memory_max = vm.memory * config.MEMORY_TO_MAX_RATIO
        assert not vm.memory_policy.max == memory_max

    @tier2
    @polarion("RHEVM-19330")
    def test_hotplug_max_memory_negative(self):
        """
        Negative: Add default vm, hotplug more memory then maximum
        """
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        assert ll_vms.runVmOnce(True, vm.name, wait_for_state='up')
        testflow.step("Negative: Hotplug more then maximum to VM")
        assert not mh_helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=vm.memory_policy.max
        )

    @tier2
    @polarion("RHEVM-19326")
    def test_update_max_memory(self):
        """
        Positive: Add default vm, update maximum memory
        """
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        assert ll_vms.runVmOnce(True, vm.name, wait_for_state='up')
        testflow.step("Positive: Update maximum memory")
        upd_maxmem = {
            'max_memory': config.MEM_FOR_UPDATE,
            'compare': False,
        }
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            **upd_maxmem
        )
        global_helper.wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        assert hl_vms.reboot_to_state(vm=self.vm_name)
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step('Positive: Check vm memory')
        assert vm.memory_policy.max == config.MEM_FOR_UPDATE

    @tier2
    @polarion("RHEVM-19337")
    def test_clone_vm_check_max_memory(self):
        """
        Positive: Add default vm, clone it update maximum memory
        """
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        testflow.step("Positive: Clone vm")
        assert hl_vms.clone_vm(
                positive=True,
                vm=self.vm_name,
                clone_vm_name=config.MAX_MEMORY_VM_TEST_CLONED
        )
        testflow.step('Positive: Check cloned VM parameters')
        assert helper.check_clone_vm(
                self.vm_name,
                config.MAX_MEMORY_VM_TEST_CLONED
        )
        assert ll_vms.runVmOnce(
            positive=True,
            vm=config.MAX_MEMORY_VM_TEST_CLONED,
            wait_for_state='up'
        )
        testflow.step('Positive: Check VM memory')
        vm = ll_vms.get_vm(config.MAX_MEMORY_VM_TEST_CLONED)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO

    @tier2
    @polarion("RHEVM-19338")
    def test_clone_vm_from_snapshot_check_max_memory(self):
        """
        Positive: Add default vm, make snapshot, clone new VM from snapshot,
        run it, check maximum memory
        """
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO
        testflow.step("Positive: Create vm snapshot")
        assert ll_vms.addSnapshot(
            positive=True,
            vm=self.vm_name,
            wait=True,
            description='max_mem_test_snapshot'
        )
        testflow.step("Create VM from snapshot")

        assert ll_vms.cloneVmFromSnapshot(
                positive=True,
                name=config.MAX_MEMORY_VM_TEST_FROM_SNAPSHOT,
                cluster=config.CLUSTER_NAME[0],
                snapshot="max_mem_test_snapshot",
                vm=self.vm_name
        )
        assert ll_vms.runVmOnce(
                positive=True,
                vm=config.MAX_MEMORY_VM_TEST_FROM_SNAPSHOT,
                wait_for_state='up'
        )
        testflow.step('Positive: Check vm memory')
        vm = ll_vms.get_vm(config.MAX_MEMORY_VM_TEST_FROM_SNAPSHOT)
        assert vm.memory_policy.max == vm.memory * config.MEMORY_TO_MAX_RATIO

    @tier2
    @polarion("RHEVM-19339")
    @pytest.mark.custom_vm_params(
        memory=global_helper.get_gb(4),
        max_memory=global_helper.get_gb(4),
    )
    def test_hotplug_max_memory_equal_negative(self):
        """
        Negative: Add vm with memory and max memory equal, hotplug memory
        """
        vm = ll_vms.get_vm(self.vm_name)
        assert vm.memory_policy.max == vm.memory
        assert ll_vms.runVmOnce(True, vm.name, wait_for_state='up')
        testflow.step("Negative: Hotplug 2 GB RAM to VM and check memory")
        assert not mh_helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.TWO_GB
        )
        assert ll_vms.restartVm(
            vm=self.vm_name,
            wait_for_status='up'
        )
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step('Positive: Check vm memory')
        assert vm.memory == global_helper.get_gb(4)
        assert vm.memory_policy.max == vm.memory


@pytest.mark.usefixtures(remove_created_vms.__name__)
class TestMaxMemVmPool(VirtTest):
    """
    Check VM pool maximum memory tests
    """
    vm_pool_config = config.VM_POOL_PARAMETERS

    @tier1
    @polarion("RHEVM-21314")
    @bz({"1438808": {}})
    @pytest.mark.usefixtures(create_vm_pool.__name__)
    def test_vm_pool_check_max_memory(self):
        """
        Positive: Add VM pool, check maximum memory for each VM
        """
        testflow.step("Positive: Get vm pool objects ")
        pool_obj = ll_vmpools.get_vm_pool_object(self.vm_pool_config['name'])
        pool_vms_objs = ll_vmpools.get_vms_in_pool(pool_obj)
        testflow.step('Positive: Check vm memory for every VM in the pool')
        for vm in pool_vms_objs:
            assert vm.memory == config.VM_MEMORY
            assert vm.memory_policy.max == (
                config.VM_MEMORY * config.MEMORY_TO_MAX_RATIO
            )
