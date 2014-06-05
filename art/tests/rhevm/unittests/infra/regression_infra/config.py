"""
Config module for data center sanity tests
"""

# This must be here so nose doesn't consider this as a test
__test__ = False


from art.test_handler import settings
from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
ENUMS = settings.opts['elements_conf']['RHEVM Enums']

TESTNAME = 'Regression mixed'

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
VDS_PASSWORD = PARAMETERS.as_list('vds_password')[0]
VDC_PORT = REST_CONNECTION['port']

DATA_CENTER_1_NAME = PARAMETERS['data_center_1_name']
DATA_CENTER_1_NAME_UPDATED = PARAMETERS['data_center_1_name_updated']
DATA_CENTER_2_NAME = PARAMETERS['data_center_2_name']
DATA_CENTER_3_NAME = PARAMETERS['data_center_3_name']

CPU_NAME = PARAMETERS['cpu_name']

CLUSTER_1_NAME = PARAMETERS['cluster_1_name']
CLUSTER_2_NAME = PARAMETERS['cluster_2_name']
CLUSTER_3_NAME = PARAMETERS['cluster_3_name']
CLUSTER_4_NAME = PARAMETERS['cluster_4_name']

HOST_NAME = PARAMETERS.as_list('vds')[0]
