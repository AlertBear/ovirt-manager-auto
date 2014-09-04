import config
from art.rhevm_api.tests_lib.low_level.vms import (
    wait_for_vm_states, get_vm_state, startVm, waitForVMState,
)


def start_vm():
    wait_for_vm_states(
        config.VM_NAME[0],
        [config.VM_UP, config.VM_DOWN, config.VM_SUSPENDED])
    if get_vm_state(config.VM_NAME[0]) != config.VM_UP:
        assert startVm(
            True, config.VM_NAME[0], config.VM_UP)
        waitForVMState(config.VM_NAME[0])
