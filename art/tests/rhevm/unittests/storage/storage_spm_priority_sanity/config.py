"""
Config module for storage SPM priority sanity
"""

__test__ = False

from . import ART_CONFIG

# Name of the test
TESTNAME = "storage_spm_priority_sanity"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['data_center_type']
STORAGE_CONF = ART_CONFIG['STORAGE']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE

SLEEP_AMOUNT = PARAMETERS.as_float('sleep_amount')

# Hosts settings
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PWD = PARAMETERS.as_list('vds_password')

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

# Priority range
MAX_VALUE = PARAMETERS.get('max_value', 10)
MIN_VALUE = PARAMETERS.get('min_value', -1)

# DB settings
DB_HOST = ART_CONFIG['REST_CONNECTION']['host']
DB_HOST_USER = 'root'
DB_HOST_PASSWORD = PARAMETERS['vdc_root_password']
DB_USER = PARAMETERS['db_user']
