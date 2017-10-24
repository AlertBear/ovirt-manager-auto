"""
Virt - Reg vms
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa
from rhevmtests.helpers import get_gb

TWO_GB = get_gb(2)

VM_MEMORY = TWO_GB
MEM_FOR_UPDATE = get_gb(10)

INSTANCE_TYPE_MEMORY = TWO_GB
MEMORY_TO_MAX_RATIO = 4
MAX_INSTANCE_TYPE_MEMORY = 4 * INSTANCE_TYPE_MEMORY
# vm names
MAX_MEMORY_VM_TEST = 'max_memory_vm_test'
MAX_MEMORY_VM_TEST_FROM_SNAPSHOT = 'max_memory_vm_test_from_snapshot'
MAX_MEMORY_VM_TEST_CLONED = 'max_memory_vm_test_cloned'
REG_VMS_LIST = [
    MAX_MEMORY_VM_TEST, MAX_MEMORY_VM_TEST_CLONED,
    MAX_MEMORY_VM_TEST_FROM_SNAPSHOT
]
# clone vm
VM_PARAMETERS = {
    'name': MAX_MEMORY_VM_TEST,
    'cluster': CLUSTER_NAME[0],
    'os_type': VM_OS_TYPE,
    'type': VM_TYPE,
    'display_type': VM_DISPLAY_TYPE,
    'memory': VM_MEMORY,
    'template': TEMPLATE_NAME[0],
    'ballooning': False,
}

VM_POOL_PARAMETERS = {
    'name': 'max_mem_vm_pool',
    'size': 5,
    'prestarted_vms': 2,
    'memory': VM_MEMORY,
    'template': 'golden_mixed_virtio_template',
    'cluster': CLUSTER_NAME[0],
}

INSTANCE_TYPE_PARAMETERS = {
    'memory': INSTANCE_TYPE_MEMORY,
    'memory_guaranteed': INSTANCE_TYPE_MEMORY / 2,
    'max_memory': MAX_INSTANCE_TYPE_MEMORY
}
CUSTOM_INSTANCE_TYPE_NAME = 'Max_Mem_Custom'
INSTANCE_TYPES = ['Tiny', 'Small', 'Medium', 'Large', 'XLarge']

