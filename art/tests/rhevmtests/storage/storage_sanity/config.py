"""
Config module for storage sanity tests
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "storage_sanity_unittest"

if not GOLDEN_ENV:
    if STORAGE_TYPE == STORAGE_TYPE_ISCSI:
        EXTEND_LUN = STORAGE_CONF['PARAMETERS.extend_lun']
        EXTEND_LUN_ADDRESS = PARAMETERS.as_list("extend_lun_address")
        EXTEND_LUN_TARGET = PARAMETERS.as_list("extend_lun_target")
        EXTEND_LUN = PARAMETERS.as_list("extend_lun")
else:
    if STORAGE_TYPE_ISCSI in STORAGE_SELECTOR:
        EXTEND_LUN_ADDRESS = UNUSED_LUN_ADDRESSES
        EXTEND_LUN_TARGET = UNUSED_LUN_TARGETS
        EXTEND_LUN = UNUSED_LUNS

UNUSED_LUNS = {
    "lun_targets": EXTEND_LUN_TARGET,
    "lun_addresses": EXTEND_LUN_ADDRESS,
    "lun_list": EXTEND_LUN
}

HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]
