"""
Config module for storage read only disks
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

VM_COUNT = 2

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

# allocation policies
SPARSE = True

# disk formats
# TODO: Remove
FORMAT_COW = DISK_FORMAT_COW
FORMAT_RAW = DISK_FORMAT_RAW

if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    DIRECT_LUN = PARAMETERS.get('direct_lun')
    DIRECT_LUN_ADDRESS = PARAMETERS.get('direct_lun_address')
    DIRECT_LUN_TARGET = PARAMETERS.get('direct_lun_target')
