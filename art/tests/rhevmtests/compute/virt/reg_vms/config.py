"""
Virt - Reg vms
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa

TWO_GB = 2 * GB
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
RHEL_TZ = ENUMS['timezone_rhel_etc_gmt']
# Timeout for VM creation in Vmpool
VMPOOL_TIMEOUT = 30
RHEL6_64 = ENUMS['rhel6x64']
WIN_2008 = ENUMS['windows2008r2x64']
WIN_7 = ENUMS['windows7']

ticket_expire_time = 120
template_name = TEMPLATE_NAME[0]
# vm names
ADD_VM_TEST = 'add_vm_test'
MIX_CASE_TEST = 'virt_mix_cases'
CLONE_VM_TEST = "tested_vm_clone_vm"
VM_FROM_BASE_TEMPLATE = 'virt_vm_from_template'
BASE_VM = 'virt_base_vm'
CPU_MODEL_VM = 'test_cpu_vm'
BASE_TEMPLATE = 'virt_base_template'
# clone vm test
TEST_CLONE_WITH_2_DISKS = "cloned_vm_with_2_disks"
TEST_CLONE_WITH_WITHOUT_DISKS = "cloned_vm_without_disks"
REG_VMS_LIST = [
    ADD_VM_TEST, MIX_CASE_TEST, VM_FROM_BASE_TEMPLATE, BASE_VM_VIRT,
    TEST_CLONE_WITH_2_DISKS, TEST_CLONE_WITH_WITHOUT_DISKS,
    CLONE_VM_TEST, CPU_MODEL_VM
]
DESCRIPTION = 'description'
# clone vm
CLONE_VM_TEST_VM_PARAMETERS = {
    VM_MEMORY: GB,
    VM_MEMORY_GUARANTEED: GB,
    VM_OS: VM_OS_TYPE,
    TYPE_VM: VM_TYPE_DESKTOP,
    VM_DISPLAY: VM_DISPLAY_TYPE,
    VM_PLACEMENT_AFFINITY: VM_MIGRATABLE,
    VM_CLUSTER: CLUSTER_NAME[0],
    DESCRIPTION: "Virt_test"
}
VCPU_4_0 = 240
VCPU_FROM_41_AND_UP = 288
VCPU_4_0_VM = "vcpu_4_0_vm"
VCPU_4_0_CLUSTER = "Cluster_4_0"
