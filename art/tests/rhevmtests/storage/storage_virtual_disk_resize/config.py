"""
Config module for storage virtual disk resize
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "virtual_disk_resize"

# TODO: remove
STORAGE_FCP = STORAGE_TYPE_FCP

STORAGE_SIZE = int(ART_CONFIG['STORAGE'].get('devices_capacity', 50))

BASE_SNAPSHOT = 'clean_os_base_snapshot'

VM_COUNT = 2

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

# allocation policies
SPARSE = True

DISK_SIZE = 6 * GB
