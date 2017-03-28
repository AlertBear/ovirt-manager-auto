"""
Config module for storage qcow2_v3 tests
"""
from rhevmtests.storage.config import *  # flake8: noqa

if STORAGE_TYPE == STORAGE_TYPE_POSIX:
    # Force POSIX to be mounted as NFS
    STORAGE_TYPE = STORAGE_TYPE_NFS

CREATE_TEMPLATE_TIMEOUT = 1800