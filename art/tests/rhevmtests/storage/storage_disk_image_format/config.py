"""
Config module for storage disk image format
"""
from rhevmtests.storage.config import *  # flake8: noqa
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)

# Name of the test
TESTNAME = "disk_image_format"


INSTALLATION = False

DISK_KWARGS = {
    "diskInterface": INTERFACE_VIRTIO,
    "installation": INSTALLATION,
    "storageDomainName": None,
}
retrieve_disk_obj = lambda x: ll_vms.getVmDisks(x)

TEST_INTERFACES = (
    INTERFACE_VIRTIO, INTERFACE_VIRTIO_SCSI
)

if PPC_ARCH:
    TEST_INTERFACES = (
        INTERFACE_VIRTIO, INTERFACE_VIRTIO_SCSI,
        INTERFACE_SPAPR_VSCSI
    )
