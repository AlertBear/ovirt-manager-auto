#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: /RHEVM3/wiki/Compute/Virt_VMs

import copy

import pytest

import config
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    instance_types as ll_instance_types
)
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier2,
)
from rhevmtests.compute.virt.fixtures import (
    create_vm, create_instance_type, edit_instance_types, remove_created_vms
)


@pytest.mark.usefixtures(
    edit_instance_types.__name__,
    remove_created_vms.__name__
)
class TestMaxMemoryUpdateInstanceTypes(VirtTest):
    """
    Check VM maximum memory tests for various instance types
    """
    vm_parameters = config.VM_PARAMETERS
    vm_name = vm_parameters['name']
    instance_types = config.INSTANCE_TYPES
    instance_type_params = config.INSTANCE_TYPE_PARAMETERS
    reg_vms = config.REG_VMS_LIST

    @tier2
    @pytest.mark.parametrize(
        "custom_vm_params", [
            polarion("RHEVM-19323")({'instance_type': 'Tiny'}),
            polarion("RHEVM-19322")({'instance_type': 'Small'}),
            polarion("RHEVM-19321")({'instance_type': 'Medium'}),
            polarion("RHEVM-19320")({'instance_type': 'Large'}),
            polarion("RHEVM-19324")({'instance_type': 'XLarge'}),
        ],
        ids=[
            "tiny",
            "small",
            "medium",
            "large",
            "xlarge",
        ]
    )
    def test_max_memory_edit_instance_type(self, custom_vm_params):
        """
        Positive: Edit instance type, add vm, check its maximum memory,
        run Vm
        """
        vm_params = copy.copy(self.vm_parameters)
        vm_params.update(custom_vm_params)
        assert ll_vms.addVm(positive=True, wait=True, **vm_params)
        testflow.step('Check VM memory and instance type')
        vm = ll_vms.get_vm(self.vm_name)
        expected_it = ll_instance_types.get_instance_type_object(
            custom_vm_params['instance_type']
        )
        assert vm.instance_type.id == expected_it.id
        assert vm.memory_policy.max / vm.memory == config.MEMORY_TO_MAX_RATIO
        assert vm.memory_policy.max == config.MAX_INSTANCE_TYPE_MEMORY
        assert ll_vms.runVmOnce(True, self.vm_name, wait_for_state='up')
        testflow.step('Check that VM is up')
        assert ll_vms.get_vm_state(self.vm_name) == 'up'

    @tier2
    @polarion("RHEVM-19325")
    @pytest.mark.custom_vm_params(instance_type='Max_Mem_Custom')
    @pytest.mark.usefixtures(create_instance_type.__name__, create_vm.__name__)
    @pytest.mark.custom_instance_type_params({
        'instance_type_name': config.CUSTOM_INSTANCE_TYPE_NAME,
    })
    def test_max_mem_create_custom(self):
        """
        Positive: Create custom instance type, add vm, check its maximum
        memory, run Vm
        """
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step('Check VM memory')
        assert vm.memory_policy.max / vm.memory == config.MEMORY_TO_MAX_RATIO
        assert vm.memory_policy.max == config.MAX_INSTANCE_TYPE_MEMORY
        ll_vms.runVmOnce(True, self.vm_name, wait_for_state='up')
        testflow.step('Check that VM is up')
        assert ll_vms.get_vm_state(self.vm_name) == 'up'
