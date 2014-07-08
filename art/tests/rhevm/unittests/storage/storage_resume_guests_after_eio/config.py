"""
Config module for resume guests after storage domain error
"""

__test__ = False

from art.rhevm_api.utils import test_utils
from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

TESTNAME = "storage_resume_guests_eio"

PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_CONF = ART_CONFIG['STORAGE']

# DC info
LOCAL = PARAMETERS['local']
STORAGE_TYPE = PARAMETERS['storage_type']

DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TESTNAME)

HOSTS = PARAMETERS.as_list('vds')
HOSTS_PWD = PARAMETERS.as_list('vds_password')

VM_NAME = PARAMETERS.get('vm_name', 'vm_%s' % TESTNAME)

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
INTERFACE_IDE = ENUMS['interface_ide']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

HOST_NICS = PARAMETERS.as_list('host_nics')

DISK_SIZE = int(PARAMETERS['disk_size'])

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
USE_AGENT = PARAMETERS['useAgent']

if STORAGE_TYPE == ENUMS['storage_type_nfs']:
    STORAGE_SERVER = PARAMETERS.as_list('static_domain_address')[0]
else:
    STORAGE_SERVER = PARAMETERS.as_list('lun_address')[0]
INTERFACE_VIRTIO = ENUMS['interface_virtio']

PARAMETERS['data_domain_address'] = PARAMETERS['static_domain_address']
PARAMETERS['data_domain_path'] = PARAMETERS['static_domain_path']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
