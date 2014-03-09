"""
Config module for storage single disk snapshot
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "storage_single_disk_snapshot"

# Storage domain names
SD_NAME = SD_NAMES_LIST[0]
SD_NAME_1 = SD_NAMES_LIST[1]

VM_NAME = 'vm_0'
DISK_SIZE = 5 * GB

COBBLER_PROFILE = PARAMETERS['cobbler_profile']
