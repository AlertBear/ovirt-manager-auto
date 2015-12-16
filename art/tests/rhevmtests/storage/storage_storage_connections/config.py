"""
Config module for manage storage connections tests
"""

__test__ = False

import copy
from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "manage_storage_conn"

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

CONNECTIONS = []

ISCSI_STORAGE_ENTRIES = {
    'lun_address': '',
    'lun_target': '',
    'lun_port': LUN_PORT,
    'luns': UNUSED_LUNS,
}

# A host will be use to copy data between domains and clean them
# afterwards. This hosts needs to be removed from the data center
HOST_FOR_MOUNT = None  # Filled in setup_package
HOST_FOR_MOUNT_IP = None  # Filled in setup_package
HOSTS_FOR_TEST = None  # Filled in setup_package
DOMAIN_ADDRESSES = None  # Filled in setup_package
DOMAIN_PATHS = None  # Filled in setup_package
EXTRA_DOMAIN_ADDRESSES = None  # Filled in setup_package
EXTRA_DOMAIN_PATHS = None  # Filled in setup_package

DATACENTER_ISCSI_CONNECTIONS = "dc_iscsi_{0}".format(TESTNAME)
CLUSTER_ISCSI_CONNECTIONS = "cl_iscsi_{0}".format(TESTNAME)
