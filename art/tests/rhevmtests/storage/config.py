"""
Storage related global config file
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG, opts

# RHEVM related constants
ENUMS = opts['elements_conf']['RHEVM Enums']

TESTNAME = "GlobalStorage"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']


# DATA CENTER SECTION
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)


# CLUSTER SECTION
CLUSTER_NAME = 'cluster_%s' % TESTNAME


# STORAGE SECTION
STORAGE_TYPE = PARAMETERS['storage_type']
