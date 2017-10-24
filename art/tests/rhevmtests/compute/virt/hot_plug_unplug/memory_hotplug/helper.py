import logging
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as global_helper
import rhevmtests.helpers as helpers
import rhevmtests.config as config

logger = logging.getLogger("memory_hotplug_helper")


def hotplug_memory_check(
    vm_name,
    memory_to_expand,
    multiplier=1,
    user_name=None,
    password=config.VMS_LINUX_PW
):
    """
    1. Check actual memory on VM
    2. Hotplug vm memory
    3. Check VM memory on engine
    4. Check memory on VM

    Args:
        vm_name(str): vm_name
        memory_to_expand(int): memory size to expand
        multiplier(int): number of time to expand memory_to_expand
        user_name (str): user name
        password (str): use password

    Returns:
        bool: True if VM memory is as expected, False otherwise
    """
    vm_resource = helpers.get_host_executor(
        ip=hl_vms.get_vm_ip(vm_name),
        username=user_name,
        password=password
    )
    hl_vms.get_memory_on_vm(vm_resource)
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
        vm_name=vm_name, expected_memory=memory_size_after,
        user_name=user_name, password=password
    )
