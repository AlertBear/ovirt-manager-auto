"""
Config module for storage vm sanity
"""

__test__ = False

import logging
from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)
PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
STORAGE_TYPE = PARAMETERS['storage_type']

# Name of the test
TESTNAME = "full_disk_tests"
STORAGE = ART_CONFIG['STORAGE']

BASENAME = "%sTestStorage" % STORAGE_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)

HOSTS = PARAMETERS.as_list('vds')

HOST_NICS = PARAMETERS.as_list('host_nics')

VM_BASE_NAME = PARAMETERS.get("vm_name", "full_disk_vm")
VM1_NAME = "full_disk_vm1_%s" % BASENAME
VM2_NAME = "full_disk_vm2_%s" % BASENAME

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

GB = 1024 ** 3
DISK_SIZE = int(PARAMETERS.get('disk_size', 5)) * GB

DATA_ROOT_DIR = PARAMETERS['data_root_dir']
DATA_DIR_CNT = PARAMETERS['data_dir_cnt']
DATA_FILE_CNT = PARAMETERS['data_file_cnt']
DEST_DIR = PARAMETERS['dest_dir']

INTERFACE_IDE = ENUMS['interface_ide']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
VIRTIO_BLK = ENUMS['interface_virtio']

COW_DISK = ENUMS['format_cow']
RAW_DISK = ENUMS['format_raw']

SNAPSHOT_OK = ENUMS['snapshot_state_ok']
NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']

VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_LOCKED = ENUMS['disk_state_locked']

ISCSI_DOMAIN = ENUMS['storage_type_iscsi']

MAX_WORKERS = PARAMETERS.get('max_workers', 4)

TEMPLATE_NAME = PARAMETERS.get('template', 'full_disk_template')
SNAPSHOT_NAME = PARAMETERS.get('snapshot_name', 'full_disk_snapshot')

STORAGE_SECTION = ART_CONFIG['STORAGE']
if STORAGE_TYPE == ISCSI_DOMAIN:
    EXTEND_LUN = STORAGE_SECTION['PARAMETERS.extend_lun']
    # Size of device (in GB)
    EXTEND_SIZE = int(EXTEND_LUN['devices_capacity'])
