"""
Config module for live storage migration
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "live_storage_migration"

BASE_SNAPSHOT = 'clean_os_base_snapshot'

VM_COUNT = 2
VM_NAME = TESTNAME + "_%s"

VM_DISK_SIZE = 10 * GB
DISK_SIZE = GB

# TODO: remove this
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']

# allocation policies
SPARSE = True

TEMPLATE_NAME_LSM = "template_lsm"
