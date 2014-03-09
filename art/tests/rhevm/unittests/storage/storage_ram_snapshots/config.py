from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Name of the test
TESTNAME = PARAMETERS['basename']

ENUMS = opts['elements_conf']['RHEVM Enums']
SD_ACTIVE = ENUMS['storage_domain_state_active']

VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']
VM_UP = ENUMS['vm_state_up']
HOST_UP = ENUMS['host_state_up']
SNAPSHOT_OK = ENUMS['snapshot_state_ok']


VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

BASENAME = PARAMETERS.get('basename', '')
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)
EXPORT_DOMAIN = 'export_domain'

HOSTS = PARAMETERS['vds']
VM_NAME = PARAMETERS['vm_name']
DISK_SIZE = 8 * GB

VM_USER = PARAMETERS.get('vm_user', 'root')
VM_PASSWORD = PARAMETERS.get('vm_linux_password')
BASE_SNAPSHOT = 'clean_os_base_snapshot'
RAM_SNAPSHOT = 'ram_snapshot_%d'


# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
