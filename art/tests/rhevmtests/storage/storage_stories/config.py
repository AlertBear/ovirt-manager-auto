"""
Config module for storage sanity tests
"""
__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "%sTestStorage" % STORAGE_TYPE

if not GOLDEN_ENV:
    DC_VERSIONS = PARAMETERS.as_list('dc_versions')
    DC_TYPE = PARAMETERS['data_center_type']
else:
    DC_VERSIONS = []
    DC_TYPE = []

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD
SETUP_ADDRESS = VDC_HOST

FIRST_HOST = HOSTS[0]
