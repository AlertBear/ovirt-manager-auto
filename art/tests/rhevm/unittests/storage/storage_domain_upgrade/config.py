"""
Config module for storage domain upgrade
"""

__test__ = False

from art.test_handler.settings import opts
from . import ART_CONFIG

# Name of the test
TESTNAME = "storage_domain_upgrade"

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

TMP_CLUSTER_NAME = 'tmp_cluster'

# Enums
ENUMS = opts['elements_conf']['RHEVM Enums']

DC_VERSIONS = PARAMETERS.as_list('dc_versions')
DC_UPGRADE_VERSIONS = PARAMETERS.as_list('dc_upgrade_versions')
DC_TYPE = PARAMETERS['data_center_type']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

SETUP_ADDRESS = ART_CONFIG['REST_CONNECTION']['host']
SETUP_PASSWORD = PARAMETERS['vdc_root_password']
