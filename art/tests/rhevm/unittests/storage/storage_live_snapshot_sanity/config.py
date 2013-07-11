"""
Config module for storage live snapshot sanity
"""

__test__ = False

from . import ART_CONFIG

# Name of the test
TESTNAME = "storage_live_snapshot_sanity"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['data_center_type']
STORAGE_CONF = ART_CONFIG['STORAGE']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE
SD_NAME_1 = "%s_1" % STORAGE_TYPE

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)
