import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.virt.config as config
import rhevmtests.virt.helper as virt_helper
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
        "vm": vm_name
    }

    memory_hotplug_kwargs = {
        "vm_name": vm_name,
        "memory_to_expand": config.GB,
        "user_name": None,
        "password": config.VMS_LINUX_PW
    }

    cpu_hotplug_kwargs = {
        "number_of_cpus": 2,
        "action": config.HOT_PLUG_CPU,
        "vm_name": vm_name,
        "user_name": None,
        "password": config.VMS_LINUX_PW
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

    start_vm_args = {
        "positive": True,
        "vm": vm_name,
        "wait_for_status": config.VM_UP,
        "wait_for_ip": False,
    }
    stop_vm_args = {
        "vms_list": [vm_name]
    }
    suspend_resume_args = {
        'vm_name': vm_name
    }
    cloud_init_args = {
        'vm_name': vm_name,
        'dns_search': None,
        'dns_servers': None,
        'time_zone': config.NEW_ZEALAND_TZ,
        'script_content': None,
        'hostname': None,
        'check_nic': False
    }

    actions_info = {
        config.MIGRATION_ACTION: (ll_vms.migrateVm, migration_kwargs),
        config.MEMORY_HOTPLUG_ACTION: (
            hotplug_memory_check, memory_hotplug_kwargs
        ),
        config.CPU_HOTPLUG_ACTION: (hot_plug_unplug_cpu, cpu_hotplug_kwargs),
        config.SNAPSHOT_MEM_ACTION: (
            virt_helper.snapshot_vm, snapshot_with_memory
        ),
        config.SNAPSHOT_NO_MEM_ACTION: (
            virt_helper.snapshot_vm, snapshot_without_memory
        ),
        config.CLONE_ACTION: (virt_helper.clone_vm, clone_vm_args),
        config.START_ACTION: (ll_vms.startVm, start_vm_args),
        config.STOP_ACTION: (ll_vms.stop_vms_safely, stop_vm_args),
        config.SUSPEND_RESUME: (
            virt_helper.suspend_resume_vm_test, suspend_resume_args
        ),
        config.CLOUD_INIT_CHECK: (
            virt_helper.check_cloud_init_parameters,
            cloud_init_args
        )
    }

    if action_name in actions_info.keys():
        func_name = actions_info[action_name][0]
        func_kwargs = actions_info[action_name][1]
        if func_args:
            func_kwargs.update(func_args)
    return func_name(**func_kwargs)
