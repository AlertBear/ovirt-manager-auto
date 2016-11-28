"""
Config module for libvirt test suite
Author: Alex Jia <ajia@redhat.com>, Bing Li <bili@redhat.com>
"""

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

__test__ = True

GB = 1024 ** 3

ENUMS = opts['elements_conf']['RHEVM Enums']

# Name of the test
TESTNAME = "libvirt_suite"

PARAMETERS = ART_CONFIG['PARAMETERS']

DATA_CENTER_TYPE = (PARAMETERS['data_center_type']).split("_")[0]
if DATA_CENTER_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['data_center_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE

DC_STATE_UP = ENUMS['data_center_state_up']
EXTEND_LUN = PARAMETERS.get('extend_lun', None)

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)

SD_TYPE = ENUMS['storage_dom_type_data']
SD_STATE_ACTIVE = ENUMS['storage_domain_state_active']
SD_NAME_0 = "%s_0" % DATA_CENTER_TYPE
SD_NAME_1 = "%s_1" % DATA_CENTER_TYPE

SD_NAMES_LIST = [SD_NAME_0, SD_NAME_1]

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
SETUP_ADDRESS = ART_CONFIG['REST_CONNECTION']['host']

HOSTS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')
VDS_USER = 'root'
FIRST_HOST = HOSTS[0]
HOST_NONOPERATIONAL = ENUMS["search_host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]
HOST_UP = ENUMS['search_host_state_up']
HOST_STATE_UP = ENUMS['host_state_up']
HOST_NICS = PARAMETERS.as_list('host_nics')
NETWORKS = PARAMETERS.as_list('networks')
SNAPSHOT_OK = ENUMS['snapshot_state_ok']

DISK_SIZE = 6 * GB
DISK_TYPE_DATA = ENUMS['disk_type_data']
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']

CPU_SOCKET = PARAMETERS.get('cpu_socket', None)
CPU_CORES = PARAMETERS.get('cpu_cores', None)
DISPLAY_TYPE = PARAMETERS.get('display_type', None)
OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

VM_NAME = 'myVM1'

VM_BASE_NAME = PARAMETERS.get("vm_name", "full_disk_vm")
VM1_NAME = "full_disk_vm1_%s" % BASENAME
VM2_NAME = "full_disk_vm2_%s" % BASENAME

VM_USER = PARAMETERS.get('vm_linux_user', None)
VM_PASSWORD = PARAMETERS.get('vm_linux_password', None)
VM_TYPE_DESKTOP = ENUMS.get('vm_type_desktop', None)

MGMT_BRIDGE = PARAMETERS.get('mgmt_bridge', None)

USE_AGENT = PARAMETERS.get('useAgent', None)

INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']
INTERFACE_VIRTIO_SCSI = ENUMS['interface_virtio_scsi']

COW_DISK = ENUMS['format_cow']
RAW_DISK = ENUMS['format_raw']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']

if DATA_CENTER_TYPE == STORAGE_TYPE_NFS:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
elif DATA_CENTER_TYPE == STORAGE_TYPE_ISCSI:
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')
    LUN_PORT = 3260

ISO_DOMAIN_NAME = 'ISO_DOMAIN'

# Migration
VM_MIGRATION = PARAMETERS.get('vm_migration', 'false')

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS.get('cobbler_profile', None)
