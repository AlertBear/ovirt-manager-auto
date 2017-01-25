"""
Config module for storage vm sanity
"""
from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "full_disk_tests"

VM1_NAME = TESTNAME + "_vm_1_%s"
VM2_NAME = TESTNAME + "_vm_2_%s"

TEMPLATE_NAME = PARAMETERS.get('template', 'full_disk_template')
SNAPSHOT_NAME = PARAMETERS.get('snapshot_name', 'full_disk_snapshot')

# TODO: remove
ISCSI_DOMAIN = "iscsi_domain"

EXTEND_LUN = None

if STORAGE_TYPE_ISCSI in STORAGE_SELECTOR:
    EXTEND_LUN_ADDRESS = UNUSED_LUN_ADDRESSES
    EXTEND_LUN_TARGET = UNUSED_LUN_TARGETS
    EXTEND_LUN = UNUSED_LUNS
    EXTEND_LUNS = []  # used in test_allocated_space
    EXTEND_SIZE = 0

if EXTEND_LUN:
    # Adds to EXTEND_LUNS a dictionary with all the luns data used to be
    # extended
    EXTEND_LUNS = []
    for address, target, lun in zip(
        EXTEND_LUN_ADDRESS, EXTEND_LUN_TARGET, EXTEND_LUN
    ):
        EXTEND_LUNS.append({
            "lun_targets": [target],
            "lun_addresses": [address],
            "lun_list": [lun],
            "override_luns": True,
        })

BASE_KWARGS = disk_args.copy()
BASE_KWARGS.update({
    "interface": VIRTIO_SCSI,
    "alias": "direct_lun_disk",
    "type_": STORAGE_TYPE_ISCSI,
})
