"""
Config module for storage spm negative
"""

from art.test_handler.settings import opts

__test__ = False

from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "storage_spm_negative"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['data_center_type']

STORAGE_DOMAIN_NAMES = list()

HOSTS = PARAMETERS.as_list('vds')
VDS_ROOT = 'root'
VDS_PASSWORDS = PARAMETERS.as_list('vds_password')

DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TESTNAME)

SSL = PARAMETERS.get('ssl', '')

if STORAGE_TYPE == ENUMS['storage_type_nfs']:
    STORAGE_SERVERS = PARAMETERS.as_list('data_domain_address') + \
        [PARAMETERS['master_export_address']]
    MASTER_VERSION_TAG = 'MASTER_VERSION'
else:
    STORAGE_SERVERS = PARAMETERS.as_list('lun_address') + \
        [PARAMETERS['master_lun_address']]
    MASTER_VERSION_TAG = 'MDT_MASTER_VERSION'

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

# For executing commands on rhevm machine
SETUP_ADDRESS = ART_CONFIG['REST_CONNECTION']['host']
SETUP_PASSWORD = PARAMETERS['vdc_root_password']
