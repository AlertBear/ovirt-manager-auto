import logging
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as global_helper
import rhevmtests.helpers as helpers

logger = logging.getLogger("memory_hotplug_helper")


def hotplug_memory_check(vm_name, memory_to_expand, multiplier=1):
    """
    1. Check actual memory on VM
    2. Hotplug vm memory
    3. Check VM memory on engine
    4. Check memory on VM

    Args:
        vm_name(str): vm_name
        memory_to_expand(int): memory size to expand
        multiplier(int): number of time to expand memory_to_expand
    Returns:
        bool: True if VM memory is as expected, False otherwise
    """
    hl_vms.get_memory_on_vm(helpers.get_vm_resource(vm_name))
    memory_size_before, memory_size_after, new_memory_size = (
        hl_vms.expand_vm_memory(vm_name, memory_to_expand, multiplier)
    )
    # engine check
    if memory_size_after == -1:
        logger.error("Hotplug failed: memory on engine did not updated")
        return False
    if memory_size_before == memory_size_after:
        logger.error("Hotplug failed: memory before and after are equals")
        return False
    logger.info("Engine check pass")
    # vm check
    return global_helper.wait_for_vm_gets_to_full_memory(
        vm_name=vm_name, expected_memory=memory_size_after
    )
