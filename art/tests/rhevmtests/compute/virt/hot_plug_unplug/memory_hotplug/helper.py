import logging
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as global_helper
import rhevmtests.helpers as helpers
import rhevmtests.compute.virt.config as config

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
        vm_name(str): VM name
        memory_to_expand(int): memory size to expand
        multiplier(int): number of time to expand memory_to_expand
        user_name (str): user name
        password (str): use password

    Returns:
        bool: True if VM memory is as expected, False otherwise
    """
    vm_resource = helpers.get_host_executor(
        ip=hl_vms.get_vm_ip(vm_name=vm_name),
        username=user_name,
        password=password
    )
    hl_vms.get_memory_on_vm(vm_resource=vm_resource)
    memory_size_before, memory_size_after, new_memory_size = (
        hl_vms.expand_vm_memory(
            vm_name=vm_name,
            mem_size_to_expand=memory_to_expand,
            number_of_times=multiplier
        )
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
        vm_name=vm_name,
        expected_memory=memory_size_after,
        user_name=user_name,
        password=password
    )


def create_snapshot_hot_unplug(vm_name):
    """
    1. Adding a snapshot with memory
    2. Hot-unplug vm memory(1GB)
    3. Stop the VM

    Args:
        vm_name(str): VM name

    Returns:
        int: The new memory of the VM
    """
    assert ll_vms.addSnapshot(
        positive=True,
        vm=vm_name,
        description=config.SNAPSHOT_MEM_ACTION,
        persist_memory=True
    ), "Failed to create snapshot"
    logger.info(
        "Reduce VM memory using memory hot-unplug: with 1GB,"
        "check memory updated"
    )
    _, _, new_memory = hl_vms.expand_vm_memory(
        vm_name=vm_name,
        mem_size_to_expand=-config.GB
    )
    logger.info("Stopping vm %s", vm_name)
    assert ll_vms.stop_vms_safely(
        vms_list=[vm_name]
    ), "Failed to stop VM"
    return new_memory


def prev_unprev_snapshot(vm_name):
    """
    1. Preview snapshot on the VM
    2. Start the VM
    3. Stop the VM
    4. Undo the preview of the snapshot
    5. Start the VM

    Args:
        vm_name(str): VM name
    """
    assert ll_vms.preview_snapshot(
        positive=True,
        vm=vm_name,
        description=config.SNAPSHOT_MEM_ACTION,
        ensure_vm_down=True,
        restore_memory=True
    ), "Failed to preview snapshot"
    logger.info("Undo preview on snapshot")
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    ), "Failed to start VM"
    assert ll_vms.stop_vms_safely(
        vms_list=[vm_name]
    ), "Failed to stop VM"
    assert ll_vms.undo_snapshot_preview(
        positive=True,
        vm=vm_name
    ), "Failed to undo snapshot preview"
    logger.info("Check memory after undo-preview snapshot")
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    ), "Failed to start VM"


def commit_snapshot_start_vm(vm_name):
    """
    1. Stop the VM
    2. Preview snapshot on the VM
    3. Commit snapshot on the VM
    4. Start the VM

    Args:
        vm_name(str): VM name
    """
    logger.info("Stopping vm %s", vm_name)
    assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    assert ll_vms.preview_snapshot(
        positive=True,
        vm=vm_name,
        description=config.SNAPSHOT_MEM_ACTION,
        ensure_vm_down=True,
        restore_memory=True
    ), "Failed to preview snapshot"
    assert ll_vms.commit_snapshot(
        positive=True,
        vm=vm_name,
        restore_memory=True
    ), "Failed to commit snapshot"
    logger.info("Start vm %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_ip=True,
        wait_for_status=config.VM_UP
    ), "Failed to start VM"


def suspend_resume_vm(vm_name):
    """
    1. Suspend the VM
    2. Resume the VM

    Args:
        vm_name(str): VM name
    """
    logger.info("Suspend vm %s", vm_name)
    assert ll_vms.suspendVm(
        positive=True,
        vm=vm_name
    ), "Failed to suspend VM"
    logger.info("Resume vm %s", vm_name)
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_ip=True
    ), "Failed to start VM"
