"""
Config module for storage bug coverage test set
"""

__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

BASENAME = "%s_storage_cov" % STORAGE_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

VM_BASE_NAME = PARAMETERS.setdefault('vm_name', "storage_bug_coverage_vm")

DISK_SIZE = int(PARAMETERS.get('disk_size', 10737418240))

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

HOSTS = PARAMETERS.as_list('vds')
PASSWORDS = PARAMETERS.as_list('vds_password')
if PARAMETERS.get('vds_admin', None) is not None:
    ADMINS = PARAMETERS.as_list('vds_admin')
else:
    ADMINS = ['root'] * len(PASSWORDS)

EXPORT_DOMAIN = PARAMETERS.get('export_domain_name')
DOMAIN_NAME_1 = '%s_0' % STORAGE_TYPE

CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

HOST_NICS = PARAMETERS.as_list('host_nics')

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

MAX_WORKERS = PARAMETERS.get('max_workers', 10)
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

USE_AGENT = PARAMETERS['useAgent']

VM_LOCK_STATE = ENUMS["vm_state_image_locked"]
VM_DOWN_STATE = ENUMS["vm_state_down"]
