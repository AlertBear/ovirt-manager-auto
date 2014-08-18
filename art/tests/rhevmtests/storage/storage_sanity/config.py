"""
Config module for storage sanity tests
"""
__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "storage_sanity_unittest"

if PARAMETERS.get('extend_lun', None):
    EXTEND_LUN = {
        "lun_targets": PARAMETERS.as_list("extend_lun_target"),
        "lun_addresses": PARAMETERS.as_list("extend_lun_address"),
        "lun_list": PARAMETERS.as_list("extend_lun"),
    }
else:
    EXTEND_LUN = None

FIRST_HOST = HOSTS[0]

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]
