"""
Config module for advanced nfs options tests
"""

__test__ = False

import copy

from art.test_handler.settings import ART_CONFIG, opts
from art.rhevm_api.utils import test_utils
from art.rhevm_api import resources

# Name of the test
TESTNAME = "golden_env"

PARAMETERS = ART_CONFIG['PARAMETERS']

REST_CONNECTION = ART_CONFIG['REST_CONNECTION']

STORAGE = copy.deepcopy(ART_CONFIG['PARAMETERS'])

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Enums
ENUMS = opts['elements_conf']['RHEVM Enums']

BASENAME = PARAMETERS.get('basename', 'golden_env')

DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASENAME)

HOSTS = PARAMETERS.as_list('vds')

PASSWORDS = PARAMETERS.as_list('vds_password')

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

CPU_NAME = PARAMETERS['cpu_name']

CLUSTER_NAME = PARAMETERS['cluster_name']

VDC = REST_CONNECTION.get('host')
VDC_PASSWORD = PARAMETERS.get('vdc_root_password')

VM_BASE_NAME = BASENAME

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

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
NIC_NAME = 'nic1'

USE_AGENT = PARAMETERS['useAgent']

HOST_NICS = PARAMETERS.as_list('host_nics')
DISK_SIZE = int(PARAMETERS['disk_size'])

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

TEMPLATE_NAME = PARAMETERS.get('template_name', 'golden_env')

STORAGE['lun'] = PARAMETERS.as_list('lun')
STORAGE['lun_address'] = PARAMETERS.as_list('lun_address')
STORAGE['lun_target'] = PARAMETERS.as_list('lun_target')

STORAGE['data_domain_address'] = PARAMETERS.as_list('data_domain_address')
STORAGE['data_domain_path'] = PARAMETERS.as_list('data_domain_path')

EPS = ART_CONFIG['EPS']
CLEAN_EXPORT_DOMAIN = PARAMETERS.as_bool('clean_export_domain')

ENGINE_HOST = resources.Host(VDC)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_PASSWORD)
)

IBM_POWER_8 = 'IBM POWER8'
IBM_POWER_8E = 'IBM POWER8E'
PPC_CPUS = [IBM_POWER_8, IBM_POWER_8E]
PPC_ARCH = True if CPU_NAME in PPC_CPUS else False
