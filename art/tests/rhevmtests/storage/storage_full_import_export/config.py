"""
Config module for full import/export sanity
"""
from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "full_disk_tests"

VM_PASSWORD = VMS_LINUX_PW

# TODO: remove
VIRTIO_SCSI = INTERFACE_VIRTIO_SCSI
VIRTIO_BLK = INTERFACE_VIRTIO_SCSI

# TODO: remove this
ISCSI_DOMAIN = STORAGE_TYPE_ISCSI
