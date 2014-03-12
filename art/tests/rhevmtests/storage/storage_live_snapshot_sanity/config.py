"""
Config module for storage live snapshot sanity
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG

# Name of the test
TESTNAME = "storage_live_snapshot_sanity"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE
SD_NAME_1 = "%s_1" % STORAGE_TYPE

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)
