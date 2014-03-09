"""
Config module for storage domain auto attach
"""
__test__ = False

from art.test_handler.settings import opts
from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

BASENAME = "%sTestStorage" % STORAGE_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME

ST_NAME = "first_storage_domain"
ST_NAME_2 = "second_storage_domain"

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

VDS = PARAMETERS.as_list('vds')

PATH = PARAMETERS.as_list('data_domain_path')
ADDRESS = PARAMETERS.as_list('data_domain_address')
LUN =  PARAMETERS.as_list('lun')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_PORT = 3260

ENUMS = opts['elements_conf']['RHEVM Enums']

