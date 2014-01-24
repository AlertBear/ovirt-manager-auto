"""
Config module for full import/export sanity
"""

__test__ = False

import logging
from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)

# Name of the test
TESTNAME = "full_disk_tests"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE = ART_CONFIG['STORAGE']

STORAGE_TYPE = PARAMETERS['storage_type']
BASENAME = "%sTestStorage" % STORAGE_TYPE
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME

DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password', None)

HOSTS = PARAMETERS.as_list('vds')
PASSWORDS = PARAMETERS.as_list('vds_password')

HOST_NICS = PARAMETERS.as_list('host_nics')


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

VM_PASSWORD = PARAMETERS.get('vm_linux_password')

DATA_ROOT_DIR = PARAMETERS['data_root_dir']
DATA_DIR_CNT = PARAMETERS['data_dir_cnt']
DATA_FILE_CNT = PARAMETERS['data_file_cnt']
DEST_DIR = PARAMETERS['dest_dir']

INTERFACE_IDE = ENUMS['interface_ide']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
VIRTIO_BLK = ENUMS['interface_virtio']

COW_DISK = ENUMS['format_cow']
RAW_DISK = ENUMS['format_raw']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']

VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_TYPE_SERVER = ENUMS['vm_type_server']

DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
DISK_LOCKED = ENUMS['disk_state_locked']

ISCSI_DOMAIN = ENUMS['storage_type_iscsi']

MAX_WORKERS = PARAMETERS.get('max_workers', 2)
