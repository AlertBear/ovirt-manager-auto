"""
Config module for storage backup restore api
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "storage_backup_restore_api"

VM_COUNT = 2

# TODO remove
DISK_INTERFACE_VIRTIO = INTERFACE_VIRTIO
VOLUME_FORMAT_COW = DISK_FORMAT_COW
SPARSE = True

DISK_INTERFACES = (ENUMS['interface_ide'], ENUMS['interface_virtio'])
DISK_FORMATS = (ENUMS['format_raw'], ENUMS['format_cow'])
