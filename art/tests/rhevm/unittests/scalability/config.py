"""
Config module for scalability tests
"""

__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "scalability_vm"
PARAMETERS = ART_CONFIG['PARAMETERS']
DATA_CENTER_TYPE = PARAMETERS['data_center_type']
STORAGE = ART_CONFIG['STORAGE']

BASENAME = "%sScale" % DATA_CENTER_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)
FAKE_CLUSTER_NAME = PARAMETERS['fake_cluster_name']

HOST_NICS = PARAMETERS.as_list('host_nics')
VM_BASE_NAME = PARAMETERS['vm_name']
VM_CNT = PARAMETERS['vm_cnt']
BULK_VM_CNT = PARAMETERS['bulk_vm_cnt']

DISK_SIZE = int(PARAMETERS['disk_size'])

TEMPLATE_NAME = PARAMETERS['template_name']

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

IS_INSTALL_VM = PARAMETERS.get('is_install_vm', None)
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

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

DWH_SERVICE = "ovirt-engine-dwhd"
DWH_WAIT = 120

CPU_URL = PARAMETERS['cpu_measure_url']
MEMORY_URL = PARAMETERS['memory_measure_url']
NETWORK_URL = PARAMETERS['network_measure_url']
IO_URL = PARAMETERS['io_measure_url']
MEASURE_RES_FILE = PARAMETERS['measure_res_file']


