"""
Config module for manage storage connections tests
"""

__test__ = False

import copy

from art.rhevm_api.utils import test_utils
from art.test_handler.settings import opts
from . import ART_CONFIG

# Name of the test
TESTNAME = "async_tasks"

PARAMETERS = ART_CONFIG['PARAMETERS']

BASENAME = PARAMETERS.get('basename', 'async_tasks')
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', "cluster_%s" % BASENAME)

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

ENUMS = opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']

HOSTS = PARAMETERS.as_list('vds')

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

PASSWORDS = PARAMETERS.as_list('vds_password')

MAX_WORKERS = PARAMETERS.get('max_workers', 10)
HOST_NICS = PARAMETERS.as_list('host_nics')
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
USE_AGENT = PARAMETERS['useAgent']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_VIRTIO = ENUMS['interface_virtio']

VM_NAME = PARAMETERS.get('vm_name', "%s_vm" % BASENAME)
TEMPLATE_NAME = PARAMETERS.get('template_name', "%s_template" % BASENAME)

VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
DISK_SIZE = int(PARAMETERS.setdefault('disk_size', 10737418240))

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

CPU_SOCKET = PARAMETERS.get('cpu_socket', 2)
CPU_CORES = PARAMETERS.get('cpu_cores', 2)
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

if STORAGE_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['storage_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

NUMBER_OF_DISKS = int(PARAMETERS.get('no_of_disks', 8))
