"""
Config module for advanced nfs options tests
"""
from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "advanced_nfs_options"

NFS_PATHS = UNUSED_DATA_DOMAIN_PATHS[:]
NFS_ADDRESSES = UNUSED_DATA_DOMAIN_ADDRESSES[:]

DISK_SIZE = GB
HOST_FOR_30_DC = {}
