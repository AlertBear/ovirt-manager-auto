"""
Config module for storage sanity tests
"""
__test__ = False


from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "domain_lifecycle"

# For 3.5 only test upgrade from 3.4
# TODO: Only execute upgrad from 3.5 because bug:
# https://bugzilla.redhat.com/show_bug.cgi?id=1244174
# DC_VERSIONS = ["3.4", "3.5",]
DC_VERSIONS = ["3.4"]
DC_UPGRADE_VERSIONS = ["3.5", "3.6"]
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

