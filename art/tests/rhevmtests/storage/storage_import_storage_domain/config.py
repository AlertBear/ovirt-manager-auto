"""
Config module for storage Import Storage Domain
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "import_storage_domain"

VM_NAME = "{0}_vm_%s".format(TESTNAME)
DISK_SIZE = 5 * GB

EXTEND_LUN = None

if not GOLDEN_ENV:
    if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
        EXTEND_LUN_ADDRESS = PARAMETERS.as_list("extend_lun_address")
        EXTEND_LUN_TARGET = PARAMETERS.as_list("extend_lun_target")
        EXTEND_LUN = PARAMETERS.as_list("extend_lun")
    elif STORAGE_TYPE == STORAGE_TYPE_NFS:
        UNUSED_DATA_DOMAIN_ADDRESSES = PARAMETERS.as_list(
            'extra_data_domain_address'
        )
        UNUSED_DATA_DOMAIN_PATHS = PARAMETERS.as_list('extra_data_domain_path')
    elif STORAGE_TYPE == STORAGE_TYPE_GLUSTER:
        UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES = PARAMETERS.as_list(
            'gluster_extra_data_domain_address'
        )
        UNUSED_GLUSTER_DATA_DOMAIN_PATHS = PARAMETERS.as_list(
            'gluster_extra_data_domain_path'
        )

else:
    if STORAGE_TYPE_ISCSI in STORAGE_SELECTOR:
        EXTEND_LUN_ADDRESS = UNUSED_LUN_ADDRESSES
        EXTEND_LUN_TARGET = UNUSED_LUN_TARGETS
        EXTEND_LUN = UNUSED_LUNS

if EXTEND_LUN:
    UNUSED_LUNS = {
        "lun_addresses": EXTEND_LUN_ADDRESS,
        "lun_targets": EXTEND_LUN_TARGET,
        "lun_list": EXTEND_LUN
    }