"""
Config module for advanced nfs options tests
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "advanced_nfs_options"

if GOLDEN_ENV:
    NFS_PATHS = UNUSED_DATA_DOMAIN_PATHS[:]
    NFS_ADDRESSES = UNUSED_DATA_DOMAIN_ADDRESSES[:]
else:
    STORAGE_CONF['data_domain_path'] = [PARAMETERS.as_list('data_domain_path')[0]]
    STORAGE_CONF['data_domain_address'] = [PARAMETERS.as_list(
        'data_domain_address')[0]]

    NFS_PATHS = PARAMETERS.as_list('data_domain_path')[1:]
    NFS_ADDRESSES = PARAMETERS.as_list('data_domain_address')[1:]

DISK_SIZE = GB
HOST_FOR_30_DC = {}
