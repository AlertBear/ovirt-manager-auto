"""
Config module for storage supervdsm
"""
__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# TODO: remove
STORAGE = STORAGE_CONF

# TODO: remove
FIRST_HOST = HOSTS[0]
FIRST_HOST_PASSWORD = HOSTS_PW

TESTNAME = "%sTestStorage" % STORAGE_TYPE

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD
