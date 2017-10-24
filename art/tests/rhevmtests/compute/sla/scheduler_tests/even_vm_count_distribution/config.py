"""
Configuration file for even_vm_count_distribution package
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

NUM_OF_VMS = 5
NUM_OF_VMS_ON_HOST = 3
DEFAULT_VMS_TO_RUN = {
    VM_NAME[0]: {VM_RUN_ONCE_HOST: 0},
    VM_NAME[1]: {VM_RUN_ONCE_HOST: 0},
    VM_NAME[2]: {VM_RUN_ONCE_HOST: 1},
    VM_NAME[3]: {VM_RUN_ONCE_HOST: 1},
    VM_NAME[4]: {VM_RUN_ONCE_HOST: 1}
}
DEFAULT_EVCD_PARAMS = {
    "HighVmCount": 2,
    "MigrationThreshold": 3,
    "SpmVmGrace": 1
}
