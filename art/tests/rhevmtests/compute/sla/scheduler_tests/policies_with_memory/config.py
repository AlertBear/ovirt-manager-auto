"""
Configuration file for scheduler_policies_with_memory package
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

# Load VMS
LOAD_NORMALUTILIZED_VMS = ["vm_normalutilized_%d" % i for i in range(3)]
LOAD_OVERUTILIZED_VMS = ["vm_overutilized_%d" % i for i in range(3)]
LOAD_MEMORY_VMS = {}

DEFAULT_VMS_TO_RUN_0 = dict(
    (VM_NAME[i], {
        VM_RUN_ONCE_HOST: i, VM_RUN_ONCE_WAIT_FOR_STATE: VM_UP
    }) for i in xrange(2)
)
DEFAULT_VMS_TO_RUN_1 = dict(
    (
        VM_NAME[i], {
            VM_RUN_ONCE_HOST: i, VM_RUN_ONCE_WAIT_FOR_STATE: VM_UP
        }
    ) for i in xrange(3)
)
MEMORY_NEAR_OVERUTILIZED = {}


def merge_dicts(dict1, dict2):
    new_dict = dict(dict1)
    new_dict.update(dict2)
    return new_dict

# Constants to create memory load on the hosts
MEMORY_LOAD_VMS_TO_RUN_0 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {LOAD_NORMALUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1}}
)
MEMORY_LOAD_VMS_TO_RUN_1 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {
        LOAD_OVERUTILIZED_VMS[0]: {VM_RUN_ONCE_HOST: 0},
        LOAD_NORMALUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1}
    }
)
MEMORY_LOAD_VMS_TO_RUN_2 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {
        LOAD_OVERUTILIZED_VMS[0]: {VM_RUN_ONCE_HOST: 0},
        LOAD_OVERUTILIZED_VMS[2]: {VM_RUN_ONCE_HOST: 2}
    }
)
MEMORY_LOAD_VMS_TO_RUN_3 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {
        LOAD_NORMALUTILIZED_VMS[0]: {VM_RUN_ONCE_HOST: 0},
        LOAD_NORMALUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1}
    }
)
MEMORY_LOAD_VMS_TO_RUN_4 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {
        LOAD_OVERUTILIZED_VMS[0]: {VM_RUN_ONCE_HOST: 0},
        LOAD_OVERUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1},
        LOAD_OVERUTILIZED_VMS[2]: {VM_RUN_ONCE_HOST: 2}
    }
)
MEMORY_LOAD_VMS_TO_RUN_5 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {
        LOAD_OVERUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1},
        LOAD_OVERUTILIZED_VMS[2]: {VM_RUN_ONCE_HOST: 2}
    },
)
MEMORY_LOAD_VMS_TO_RUN_6 = merge_dicts(
    DEFAULT_VMS_TO_RUN_1,
    {
        LOAD_OVERUTILIZED_VMS[0]: {VM_RUN_ONCE_HOST: 0},
        LOAD_OVERUTILIZED_VMS[1]: {VM_RUN_ONCE_HOST: 1}
    }
)
MEMORY_LOAD_VMS_TO_RUN_7 = merge_dicts(
    DEFAULT_VMS_TO_RUN_0,
    {LOAD_OVERUTILIZED_VMS[2]: {VM_RUN_ONCE_HOST: 2}}
)

# Constants to create CPU load on hosts
HOST_CPU_LOAD_0 = {CPU_LOAD_50: [0]}
HOST_CPU_LOAD_1 = {CPU_LOAD_100: [0]}
HOST_CPU_LOAD_2 = {CPU_LOAD_50: [1]}
HOST_CPU_LOAD_3 = {CPU_LOAD_50: [1], CPU_LOAD_100: [0]}
HOST_CPU_LOAD_4 = {CPU_LOAD_50: xrange(2)}
HOST_CPU_LOAD_5 = {CPU_LOAD_100: [1]}
HOST_CPU_LOAD_6 = {CPU_LOAD_100: xrange(2)}
HOST_CPU_LOAD_7 = {CPU_LOAD_100: [0, 2]}

RESERVED_MEMORY = 65 * MB
