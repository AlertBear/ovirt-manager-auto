from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']

# Name of the test
TESTNAME = PARAMETERS['basename']

ENUMS = opts['elements_conf']['RHEVM Enums']
SD_ACTIVE = ENUMS['storage_domain_state_active']

VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']
VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']
VM_POWER_UP = ENUMS['vm_state_powering_up']
VM_POWER_DOWN = ENUMS['vm_state_powering_down']
VM_SUSPENDED = ENUMS['vm_state_suspended']
VM_START = 'start'
VM_STOP = 'stop'
VM_SUSPEND = 'suspend'
HOST_UP = ENUMS['host_state_up']
SNAPSHOT_OK = ENUMS['snapshot_state_ok']


VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

BASENAME = PARAMETERS.get('basename', '')
STORAGE_TYPE = PARAMETERS['storage_type']
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)
EXPORT_DOMAIN = 'export_domain'

HOSTS = PARAMETERS['vds']
VM_NAME = PARAMETERS['vm_name']
DISK_SIZE = 8 * GB

VM_USER = PARAMETERS.get('vm_user', 'root')
VM_PASSWORD = PARAMETERS.get('vm_linux_password')


# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']


IDE = ENUMS['interface_ide']
VIRTIO = ENUMS['interface_virtio']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

DISK_FORMAT_COW = ENUMS['format_cow']
DISK_FORMAT_RAW = ENUMS['format_raw']
