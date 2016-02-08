"""
Config module for storage Import Storage Domain
"""
from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "import_storage_domain"

VM_NAME = "{0}_vm_%s".format(TESTNAME)

EXTEND_LUN = None

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
