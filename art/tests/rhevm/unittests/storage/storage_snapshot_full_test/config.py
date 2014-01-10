"""
Config module for full snapshot test
"""

__test__ = False

from . import ART_CONFIG
from art.test_handler.settings import opts

# Name of the test
TESTNAME = "storage_snapshot_full"

PARAMETERS = ART_CONFIG['PARAMETERS']

ENUMS = opts['elements_conf']['RHEVM Enums']

SD_ACTIVE = ENUMS['storage_domain_state_active']

VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']
VM_UP = ENUMS['vm_state_up']
HOST_UP = ENUMS['host_state_up']
SNAPSHOT_OK = ENUMS['snapshot_state_ok']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Workers for thread pool
MAX_WORKERS = PARAMETERS.get('max_workers', 16)

BASE_SNAPSHOT = 'clean_os_base_snapshot'
VM_NAME = PARAMETERS['vm_name']
DATA_CENTER_TYPE = PARAMETERS['data_center_type']
EXPORT_DOMAIN = 'export_domain'

# Storage domain names
SD_NAME = "%s_0" % DATA_CENTER_TYPE
SD_NAME_1 = "%s_1" % DATA_CENTER_TYPE

VM_USER = PARAMETERS.get('vm_user', 'root')
VM_PASSWORD = PARAMETERS.get('vm_linux_password')
RAM_SNAPSHOT = 'ram_snapshot_%d'

HOSTS = PARAMETERS['vds']
GB = 1024 ** 3
DISK_SIZE = 8 * GB

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

MAX_DESC_LENGTH = 4000
SPECIAL_CHAR_DESC = '!@#$\% ^&*/\\'
