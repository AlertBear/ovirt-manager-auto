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

if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    if GOLDEN_ENV:
        DIRECT_LUN = UNUSED_LUNS[1]
        DIRECT_LUN_ADDRESS = UNUSED_LUN_ADDRESSES[1]
        DIRECT_LUN_TARGET = UNUSED_LUN_TARGETS[1]
    else:
        DIRECT_LUN = PARAMETERS.get('direct_lun')
        DIRECT_LUN_ADDRESS = PARAMETERS.get('direct_lun_address')
        DIRECT_LUN_TARGET = PARAMETERS.get('direct_lun_target')
