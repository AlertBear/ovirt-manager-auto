import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.unittest_lib.common import testflow
from rhevmtests.compute.virt import config
from art.rhevm_api.utils.test_utils import wait_for_tasks
from rhevmtests.compute.virt.fixtures import(  # flake8: noqa
    create_vm_class
)


@pytest.fixture(scope="function")
def reboot_vm(request, create_vm_class):
    """
    Stop vm, update memory to 1 GB, start vm and update VM IP
    """
    vm_name = config.MEMORY_HOTPLUG_VM

    testflow.setup("Stopping vm %s", vm_name)
    assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    wait_for_tasks(
        engine=config.ENGINE,
        datacenter=config.DATA_CENTER_NAME
    )
    testflow.setup("Update vm memory to 1 GB")
    assert hl_vms.update_vms_memory(
        vms_list=[vm_name],
        memory=config.GB
    )
    testflow.setup("Start vm %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_ip=True,
        wait_for_status=config.VM_UP
    )
    request.cls.vm_ip = hl_vms.get_vm_ip(vm_name=vm_name)
    testflow.setup("VM is up and ip is: %s", request.cls.vm_ip)
