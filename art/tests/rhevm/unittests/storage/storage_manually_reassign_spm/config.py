from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']

TESTNAME = PARAMETERS.get('basename', None)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

BASENAME = PARAMETERS.get('basename', None)
DATA_CENTER_TYPE = PARAMETERS['data_center_type']
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)

HOSTS = PARAMETERS.as_list('vds')
HOST_USER = PARAMETERS.get('vds_user', 'root')
HOST_PASSWORD = PARAMETERS['vds_password']
DEFAULT_SPM_PRIORITY = '5'