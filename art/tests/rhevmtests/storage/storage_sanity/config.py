"""
Config module for storage sanity tests
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "storage_sanity_unittest"
HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]
