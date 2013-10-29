__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

TEST_NAME = "Upgrade"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['data_center_type']

CURRENT = PARAMETERS.get('current')
basename = TEST_NAME
DC_NAME = PARAMETERS.get('dc_name', '%s_DC' % basename)
CLUSTER_NAME = PARAMETERS.get('cluster_name', '%s_Cluster' % basename)
CPU_NAME = PARAMETERS['cpu_name']
DATA_NAME = PARAMETERS.get('data_domain_name', '%s_storage' % basename)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_ADDRESSES = PARAMETERS.as_list('data_domain_address')
VERSION = PARAMETERS['compatibility_version']
HOSTS = PARAMETERS.as_list('vds')
HOSTS_PW = PARAMETERS.as_list('vds_password')[0]
HOSTS_USER = 'root'
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
TIMEOUT = 7200
SD_SUFFIX = '_sd'
STORAGE_NAME = DC_NAME + SD_SUFFIX + "0"
VM_NAME = PARAMETERS.as_list('vm_name')[0]

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
RHEVM_NAME = REST_CONNECTION['host']
MB = 1024 * 1024
GB = 1024 * MB
