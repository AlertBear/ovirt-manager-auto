"""
Config module for storage sanity tests
"""
__test__ = False


from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "domain_lifecycle"

DC_VERSIONS = ["3.0", "3.1", "3.2"]
DC_UPGRADE_VERSIONS = ["3.1", "3.2", "3.3"]
LIFECYCLE_VM = "%s_vm" % TESTNAME

FIRST_HOST = HOSTS[0]
TMP_CLUSTER_NAME = "%s_tmp_cluster" % TESTNAME

EXTRA_SD_INDEX = 3
# Generate names for the tests
LIFECYCLE_DOMAIN_NAMES = [
    "%s_%s" % (TESTNAME, idx) for idx in range(EXTRA_SD_INDEX)]
LIFECYCLE_ADDRESS = []
LIFECYCLE_PATH = []
GLUSTER_LIFECYCLE_ADDRESS = []
GLUSTER_LIFECYCLE_PATH = []
LIFECYCLE_LUNS = []
LIFECYCLE_LUN_ADDRESS = []
LIFECYCLE_LUN_TARGET = []

if STORAGE_TYPE == STORAGE_TYPE_POSIX:
    # force the posix to be mount as nfs
    STORAGE_TYPE = STORAGE_TYPE_NFS

