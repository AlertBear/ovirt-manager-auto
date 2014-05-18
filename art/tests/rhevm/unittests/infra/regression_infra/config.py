"""
Config module for data center sanity tests
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

TESTNAME = 'Regression mixed'

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
VDS_PASSWORD = PARAMETERS.as_list('vds_password')[0]
VDC_PORT = REST_CONNECTION['port']

DATA_CENTER_1_NAME = PARAMETERS['data_center_1_name']
DATA_CENTER_1_NAME_UPDATED = PARAMETERS['data_center_1_name_updated']
DATA_CENTER_2_NAME = PARAMETERS['data_center_2_name']
DATA_CENTER_3_NAME = PARAMETERS['data_center_3_name']

CPU_NAME = PARAMETERS['cpu_name']
CLUSTER_NAME = PARAMETERS['cluster_name']

HOST_NAME = PARAMETERS.as_list('vds')[0]
