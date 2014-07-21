"""
Config module for advanced nfs options tests
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "advanced_nfs_options"

# TODO remove
STORAGE_CONF['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
STORAGE_CONF['data_domain_address'] = [PARAMETERS.as_list(
    'data_domain_address')[0]]

# TODO remove
NFS_PATH = PARAMETERS.as_list('data_domain_path')[1:]
NFS_ADDRESS = PARAMETERS.as_list('data_domain_address')[1:]

HOST_FOR_30_DC = HOSTS[-1]

DISK_SIZE = GB
