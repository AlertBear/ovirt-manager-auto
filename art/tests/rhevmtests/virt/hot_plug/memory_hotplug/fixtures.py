import pytest
from art.unittest_lib.common import testflow
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.helpers as helper
from rhevmtests.virt import config


@pytest.fixture(scope="module")
def memory_hotplug_setup(request):
    """
    Setup/teardown for memory hotplug module.
    Setup: Create vm from template.
    Teardown: Remove vm.
    """

    vm_name = config.MEMORY_HOTPLUG_VM

    def fin():
        ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    testflow.setup("Create vm %s for memory hotplug test", vm_name)
    assert ll_vms.createVm(
        positive=True, vmName=vm_name,
        vmDescription=vm_name,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
        os_type=config.VM_OS_TYPE,
        display_type=config.VM_DISPLAY_TYPE,
        network=config.MGMT_BRIDGE,
        max_memory=helper.get_gb(12)
    )
    testflow.setup("Disable ballooning on VM")
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        ballooning=False
    )


@pytest.fixture(scope="function")
def reboot_vm(request, memory_hotplug_setup):
    """
    Stop vm, update memory to 1 GB, start vm and update VM IP
    """
    vm_name = config.MEMORY_HOTPLUG_VM

    testflow.setup("Stopping vm %s", vm_name)
    assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    testflow.setup("Update vn memory to 1 GB")
    assert hl_vms.update_vms_memory(vms_list=[vm_name], memory=config.GB)
    testflow.setup("Start vm %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name], wait_for_ip=True, wait_for_status=config.VM_UP
    )
    request.cls.vm_ip = hl_vms.get_vm_ip(vm_name=vm_name)
    testflow.setup("VM is up and ip is: %s", request.cls.vm_ip)
