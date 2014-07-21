"""
Config module for storage domain upgrade
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "storage_domain_upgrade"

TMP_CLUSTER_NAME = 'tmp_cluster'

# TODO remove
SETUP_ADDRESS = VDC_HOST
SETUP_PASSWORD = VDC_ROOT_PASSWORD

DC_UPGRADE_VERSIONS = PARAMETERS.as_list('dc_upgrade_versions')
DC_VERSIONS = PARAMETERS.as_list('dc_versions')
