"""
Config module for storage read only disks
"""

__test__ = False

from art.rhevm_api.utils import test_utils
from . import ART_CONFIG
from art.test_handler.settings import opts


ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "read_only_disks"

PARAMETERS = ART_CONFIG['PARAMETERS']

GB = 1024 ** 3

# DC info
LOCAL = PARAMETERS['local']
STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_FCP = ENUMS['storage_type_fcp']

BLOCK_TYPES = [STORAGE_TYPE_ISCSI, STORAGE_FCP]
CPU_NAME = PARAMETERS.get('cpu_name')

BASE_SNAPSHOT = 'clean_os_base_snapshot'

# Data-center name
DC_NAME = PARAMETERS.setdefault('dc_name', 'datacenter_%s' % TESTNAME)
if STORAGE_TYPE == STORAGE_TYPE_NFS:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')

    DIRECT_LUN = PARAMETERS.get('direct_lun')
    DIRECT_LUN_ADDRESS = PARAMETERS.get('direct_lun_address')
    DIRECT_LUN_TARGET = PARAMETERS.get('direct_lun_target')

    LUN_PORT = 3260

DISK_SIZE = 6 * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
BLOCK_FS = STORAGE_TYPE in BLOCK_TYPES

# Cluster name

CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", 'cluster_%s' % TESTNAME)

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE
SD_NAME_1 = "%s_1" % STORAGE_TYPE
SD_ACTIVE = ENUMS['storage_domain_state_active']

# Workers for thread pool
MAX_WORKERS = int(PARAMETERS.get('max_workers', 4))

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

VM_COUNT = 2

VM_USER = PARAMETERS['vm_linux_user']
VM_PASSWORD = PARAMETERS['vm_linux_password']
VM_NAME = 'vm_0'
VM_PAUSED = ENUMS['vm_state_paused']
VM_UP = ENUMS['vm_state_up']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

HOSTS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')
VDS_USER = PARAMETERS.as_list('vds_admin')

# allocation policies
SPARSE = True

# disk interfaces
VIRTIO = ENUMS['interface_virtio']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']

# disk formats
FORMAT_COW = ENUMS['format_cow']
FORMAT_RAW = ENUMS['format_raw']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']

SNAPSHOT_OK = ENUMS['snapshot_state_ok']
PREVIEW = ENUMS['preview_snapshot']
UNDO = ENUMS['undo_snapshot']
COMMIT = ENUMS['commit_snapshot']
