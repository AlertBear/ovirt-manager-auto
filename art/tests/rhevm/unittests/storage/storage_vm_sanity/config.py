"""
Config module for storage vm sanity
"""

__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "storage_vm_sanity"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE = ART_CONFIG['STORAGE']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

BASENAME = "%sTestStorage" % STORAGE_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

HOST_NICS = PARAMETERS.as_list('host_nics')
VM_BASE_NAME = PARAMETERS['vm_name']

DISK_SIZE = int(PARAMETERS['disk_size'])

TEMPLATE_NAME = PARAMETERS['template_name']

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

USE_AGENT = PARAMETERS['useAgent']

DATA_ROOT_DIR = PARAMETERS['data_root_dir']
DATA_DIR_CNT = PARAMETERS['data_dir_cnt']
DATA_FILE_CNT = PARAMETERS['data_file_cnt']
DEST_DIR = PARAMETERS['dest_dir']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

MAX_WORKERS = 4

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)

EXTENT_SIZE = 128 * 1024 * 1024
