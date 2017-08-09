import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.virt.config as config
import rhevmtests.virt.helper as virt_helper
from art.unittest_lib import testflow
from rhevmtests.virt.hot_plug_unplug.cpu.helper import (
    hot_plug_unplug_cpu
)
from rhevmtests.virt.hot_plug_unplug.memory_hotplug.helper import (
    hotplug_memory_check
)


def vm_life_cycle_action(vm_name, action_name, func_args=None):
    """
    run action on tested vm with action parameters

    Args:
        vm_name (str): vm name
        action_name (str): action to run on vm
        func_args (dict): (optional) if action parameters are not as default

    Returns:
         bool: True is action succeed, False otherwise
    """
    func_name = None
    func_kwargs = dict

    migration_kwargs = {
        "positive": True,
        "vm_name": vm_name
    }

    memory_hotplug_kwargs = {
        "vm_name": vm_name,
        "memory_to_expand": 1
    }

    cpu_hotplug_kwargs = {
        "number_of_cpus": 1,
        "action": config.HOT_PLUG_CPU,
        "vm_name": vm_name
    }

    snapshot_with_memory = {
        "vm_name": vm_name,
        "snapshot_description": config.SNAPSHOT_DESCRIPTION,
        "with_memory": True,
        "start_vm": False
    }

    snapshot_without_memory = {
        "vm_name": vm_name,
        "snapshot_description": config.SNAPSHOT_DESCRIPTION,
        "with_memory": False,
        "start_vm": False
    }

    clone_vm_args = {
        "base_vm_name": vm_name,
        "clone_vm_name": config.CLONE_VM_NAME
    }

    if action_name == config.MIGRATION_ACTION:
        testflow.step("Migrate vm %s", vm_name)
        func_name = ll_vms.migrateVm
        func_kwargs = migration_kwargs if func_args is None else func_args

    if action_name == config.MEMORY_HOTPLUG_ACTION:
        testflow.step("Memory hotplug on vm %s", vm_name)
        func_name = hotplug_memory_check
        func_kwargs = (
            memory_hotplug_kwargs if func_args is None else func_args
        )

    if action_name == config.CPU_HOTPLUG_ACTION:
        testflow.step("CPU hotplug on vm %s", vm_name)
        func_name = hot_plug_unplug_cpu
        func_kwargs = cpu_hotplug_kwargs if func_args is None else func_args

    if action_name == config.SNAPSHOT_MEM_ACTION:
        testflow.step("Snapshot with memory on vm %s", vm_name)
        func_name = virt_helper.snapshot_vm
        func_kwargs = (
            snapshot_with_memory if func_args is None else func_args
        )

    if action_name == config.SNAPSHOT_NO_MEM_ACTION:
        testflow.step("Snapshot without memory on vm %s", vm_name)
        func_name = virt_helper.snapshot_vm
        func_kwargs = (
            snapshot_without_memory if func_args is None else func_args
        )

    if action_name == config.CLONE_ACTION:
        testflow.step("Clone vm %s", vm_name)
        func_name = virt_helper.clone_vm
        func_kwargs = clone_vm_args if func_args is None else func_args

    return func_name(**func_kwargs)
