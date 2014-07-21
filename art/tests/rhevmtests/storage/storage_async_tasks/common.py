from art.rhevm_api.tests_lib.low_level import vms

import config


def start_vm():
    vms.wait_for_vm_states(
        config.VM_NAME[0],
        [config.ENUMS['vm_state_up'], config.ENUMS['vm_state_down'],
         config.ENUMS['vm_state_suspended']])
    vm_status = vms.VM_API.find(config.VM_NAME[0]).get_status().get_state()
    if vm_status != config.ENUMS['vm_state_up']:
        assert vms.startVm(
            True, config.VM_NAME[0], config.ENUMS['vm_state_up'], timeout=600)
