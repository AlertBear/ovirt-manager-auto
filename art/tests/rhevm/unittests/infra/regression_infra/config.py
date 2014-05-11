"""
Config module for data center sanity tests
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']

TESTNAME = 'Regression mixed - data centers'

DATA_CENTER_1_NAME = PARAMETERS['data_center_1_name']
DATA_CENTER_1_NAME_UPDATED = PARAMETERS['data_center_1_name_updated']
DATA_CENTER_2_NAME = PARAMETERS['data_center_2_name']
DATA_CENTER_3_NAME = PARAMETERS['data_center_3_name']
COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']
