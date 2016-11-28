"""
Config module for example
"""

# Our chance to access config object of config file
from art.test_handler.settings import ART_CONFIG

# This must be here so nose doesn't consider this as a test
__test__ = False

# Name of the test
TESTNAME = "example"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['data_center_type']
STORAGE_CONF = ART_CONFIG[STORAGE_TYPE.upper()]

DATA_CENTER_NAME = PARAMETERS.get('dc_name', "datacenter_%s" % TESTNAME)

VM_NAME = PARAMETERS.get('vm_name', 'vm_name')

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)
