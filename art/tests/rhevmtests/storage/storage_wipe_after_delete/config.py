"""
Config module for live wipe after delete
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "wipe_after_delete"

DISK_SIZE = 5 * GB

SD_NAME = SD_NAMES_LIST[0]
SD_NAME_1 = SD_NAMES_LIST[1]

VM_NAME = 'vm_0'
