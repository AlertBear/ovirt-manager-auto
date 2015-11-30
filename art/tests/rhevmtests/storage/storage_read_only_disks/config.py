"""
Config module for storage read only disks
"""
from rhevmtests.storage.config import *  # flake8: noqa

TEST_NAME = "read_only"
VM_NAME = "{0}_vm_%s".format(TEST_NAME)

VM_COUNT = 2

# allocation policies
SPARSE = True

DISK_SIZE = 1 * GB
VM_DISK_SIZE = 10 * GB

DIRECT_LUNS = UNUSED_LUNS
DIRECT_LUN_ADDRESSES = UNUSED_LUN_ADDRESSES
DIRECT_LUN_TARGETS = UNUSED_LUN_TARGETS
