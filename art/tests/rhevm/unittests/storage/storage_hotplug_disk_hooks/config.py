"""
Config module for storage hotplug disk hooks
"""

__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "hotplug_disk_hooks"
PARAMETERS = ART_CONFIG['PARAMETERS']
DATA_CENTER_TYPE = PARAMETERS['data_center_type']
STORAGE = ART_CONFIG['STORAGE']

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME
DEFAULT_VM_NAME = "vm_%s" % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

HOST_NICS = PARAMETERS.as_list('host_nics')
VM_BASE_NAME = PARAMETERS.setdefault('vm_name', DEFAULT_VM_NAME)

DISK_SIZE = int(PARAMETERS.setdefault('disk_size', 10737418240))

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

COBBLER_PROFILE = PARAMETERS['cobbler_profile']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

USE_AGENT = PARAMETERS['useAgent']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']

MAX_WORKERS = 10

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

HOSTS = PARAMETERS.as_list("vds")
ADMINS = PARAMETERS.as_list("vds_admin")
PASSWORDS = PARAMETERS.as_list("vds_password")
