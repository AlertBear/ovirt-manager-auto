"""
Config module for storage virtual disk resize
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "virtual_disk_resize"

BASE_SNAPSHOT = 'clean_os_base_snapshot'

# allocation policies
SPARSE = True

DISK_SIZE = 6 * GB

VM_NAME = TESTNAME
