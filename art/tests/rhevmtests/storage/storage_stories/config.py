"""
Config module for storage sanity tests
"""
__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "%sTestStorage" % STORAGE_TYPE

DC_VERSIONS = PARAMETERS.as_list('dc_versions')
DC_TYPE = PARAMETERS['data_center_type']

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD
SETUP_ADDRESS = VDC_HOST

# TODO: remove
VDS_PASSWORD = HOSTS_PW
VDS_USER = HOSTS_USER
FIRST_HOST = HOSTS[0]
