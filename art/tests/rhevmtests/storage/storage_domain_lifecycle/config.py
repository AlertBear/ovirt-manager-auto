"""
Config module for storage domain lifecycle tests
"""
from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "domain_lifecycle"

DC_VERSIONS = VERSION[-2:]
DC_UPGRADE_VERSIONS = [COMPATIBILITY_VERSION]
LIFECYCLE_VM = "%s_vm" % TESTNAME

EXTRA_SD_INDEX = 3

LIFECYCLE_ADDRESS = []
LIFECYCLE_PATH = []
GLUSTER_LIFECYCLE_ADDRESS = []
GLUSTER_LIFECYCLE_PATH = []
LIFECYCLE_LUNS = []
LIFECYCLE_LUN_ADDRESS = []
LIFECYCLE_LUN_TARGET = []

if STORAGE_TYPE == STORAGE_TYPE_POSIX:
    # Force POSIX to be mounted as NFS
    STORAGE_TYPE = STORAGE_TYPE_NFS
