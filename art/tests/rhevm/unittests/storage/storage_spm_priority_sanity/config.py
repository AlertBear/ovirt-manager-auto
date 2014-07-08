"""
Config module for storage SPM priority sanity
"""
from art.test_handler.settings import opts

__test__ = False

from art.test_handler.settings import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "storage_spm_priority_sanity"

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE_CONF = ART_CONFIG['STORAGE']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE


# Hosts settings
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PWD = PARAMETERS.as_list('vds_password')

VDS_ROOT = 'root'
VDS_PASSWORDS = PARAMETERS.as_list('vds_password')

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

# Storage Servers
if STORAGE_TYPE == ENUMS['storage_type_nfs']:
    STORAGE_SERVERS = PARAMETERS.as_list('data_domain_address') + \
        [PARAMETERS['master_export_address']]
    MASTER_VERSION_TAG = 'MASTER_VERSION'
else:
    STORAGE_SERVERS = PARAMETERS.as_list('lun_address') + \
        [PARAMETERS['master_lun_address']]
    MASTER_VERSION_TAG = 'MDT_MASTER_VERSION'
