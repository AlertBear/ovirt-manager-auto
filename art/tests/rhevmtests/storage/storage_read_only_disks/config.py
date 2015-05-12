"""
Config module for storage read only disks
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TEST_NAME = "read_only"
VM_NAME = "{0}_vm_%s".format(TEST_NAME)

VM_COUNT = 2

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

# allocation policies
SPARSE = True

DISK_SIZE = GB
VM_DISK_SIZE = 10 * GB

# disk formats
# TODO: Remove
FORMAT_COW = DISK_FORMAT_COW
FORMAT_RAW = DISK_FORMAT_RAW

if GOLDEN_ENV:
    DIRECT_LUNS = UNUSED_LUNS
    DIRECT_LUN_ADDRESSES = UNUSED_LUN_ADDRESSES
    DIRECT_LUN_TARGETS = UNUSED_LUN_TARGETS
else:
    if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
        DIRECT_LUNS = PARAMETERS.as_list("extend_lun")
        DIRECT_LUN_ADDRESSES = PARAMETERS.as_list("extend_lun_address")
        DIRECT_LUN_TARGETS = PARAMETERS.as_list("extend_lun_target")
