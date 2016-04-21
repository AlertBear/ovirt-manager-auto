"""
Configuration file for even_vm_count_distribution package
"""
from rhevmtests.sla.config import *  # flake8: noqa

NUM_OF_VM_NAME = 5
HOST_START_INDEX = 2
NUM_OF_VMS_ON_HOST = 3
EVEN_VM_COUNT_DISTRIBUTION_PARAMS = {
    'HighVmCount': 2,
    'MigrationThreshold': 2,
    'SpmVmGrace': 1
}
