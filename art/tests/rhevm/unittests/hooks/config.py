"""
Config module for hooks test
"""

__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from art.test_handler.settings import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']
PARAMETERS = ART_CONFIG['PARAMETERS']

STORAGE_TYPE = PARAMETERS['storage_type']

TESTNAME = "hooks"
STORAGE = ART_CONFIG['STORAGE']

BASENAME = "%sStorage" % STORAGE_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

VDC = PARAMETERS.get('host', None)
VDC_USER = PARAMETERS.get('host_user', 'root')
VDC_PASSWORD = PARAMETERS.get('password', None)
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', 'qum5net')

HOST = PARAMETERS.as_list('vds')[0]
HOST_USER = PARAMETERS.get('vds_user', 'root')
HOST_PASSWORD = PARAMETERS.as_list('vds_password')[0]

HOST_NICS = PARAMETERS.as_list('host_nics')

VM_BASE_NAME = PARAMETERS.get('vm_name', 'hooks')
VM_NAME = 'vm_%s' % BASENAME
VM_UP = ENUMS['vm_state_up']

CPU_SOCKET = PARAMETERS.get('cpu_socket', 1)
CPU_CORES = PARAMETERS.get('cpu_cores', 1)
DISPLAY_TYPE = PARAMETERS.get('display_type', 'spice')
VM_LINUX_USER = PARAMETERS.get('vm_linux_user', 'root')
VM_LINUX_PASSWORD = PARAMETERS.get('vm_linux_password', 'qum5net')
PGPASS = PARAMETERS.get('pg_pass', 'qum5net')

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge', 'rhevm')
USE_AGENT = PARAMETERS['useAgent']

GB = 1024 ** 3
DISK_SIZE = int(PARAMETERS.get('disk_size', 3)) * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_INTERFACE = ENUMS['interface_virtio']

TEMPLATE_NAME = PARAMETERS.get('template', 'hooks_temaplte')

TCMS_PLAN_CUSTOM = PARAMETERS.get('tcms_plan_custom', 10054)
TCMS_PLAN_VNIC = PARAMETERS.get('tcms_plan_vnic', 10167)

VER = PARAMETERS['compatibility_version']

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'
VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]

CUSTOM_PROPERTY = "UserDefinedVMProperties='auto_custom_hook=^[0-9]+$'"
CUSTOM_PROPERTY_VNIC = ("""CustomDeviceProperties='{type=interface;"""
                        """prop={speed=^([0-9]{1,5})$;"""
                        """port_mirroring=^(True|False)$;"""
                        """bandwidth=^([0-9]{1,5})$}}'""")
