"""
Config module for storage sanity tests
"""
__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

GB = 1024 ** 3

ENUMS = opts['elements_conf']['RHEVM Enums']

PARAMETERS = ART_CONFIG['PARAMETERS']

DATA_CENTER_TYPE = (PARAMETERS['data_center_type']).split("_")[0]
if DATA_CENTER_TYPE == ENUMS['storage_type_posixfs']:
    VFS_TYPE = (PARAMETERS['data_center_type']).split("_")[1]
    PARAMETERS['vfs_type'] = VFS_TYPE

EXTEND_LUN = PARAMETERS.get('extend_lun', None)

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASENAME)

SD_STATE_ACTIVE = ENUMS['storage_domain_state_active']
SD_NAME_0 = "%s_0" % DATA_CENTER_TYPE
SD_NAME_1 = "%s_1" % DATA_CENTER_TYPE
SD_NAME_2 = "%s_2" % DATA_CENTER_TYPE

SD_NAMES_LIST = [SD_NAME_0, SD_NAME_1, SD_NAME_2]

DC_VERSIONS = PARAMETERS.as_list('dc_versions')
DC_UPGRADE_VERSIONS = PARAMETERS.as_list('dc_upgrade_versions')
DC_TYPE = PARAMETERS['data_center_type']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
SETUP_ADDRESS = ART_CONFIG['REST_CONNECTION']['host']

HOSTS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')
VDS_USER = PARAMETERS.as_list('vds_admin')
FIRST_HOST = HOSTS[0]
HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["host_state_non_responsive"]
HOST_UP = ENUMS['search_host_state_up']
HOST_NICS = PARAMETERS.as_list('host_nics')


DISK_SIZE = 6 * GB
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']

CPU_SOCKET = PARAMETERS['cpu_socket']
CPU_CORES = PARAMETERS['cpu_cores']
DISPLAY_TYPE = PARAMETERS['display_type']
OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

COMPATIBILITY_VERSION = PARAMETERS['compatibility_version']

VM_NAME = 'vm_for_test'
VM_USER = PARAMETERS['vm_linux_user']
VM_PASSWORD = PARAMETERS['vm_linux_password']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']
VM_STATE_UP = ENUMS['vm_state_up']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

USE_AGENT = PARAMETERS['useAgent']

INTERFACE_VIRTIO = ENUMS['interface_virtio']
INTERFACE_IDE = ENUMS['interface_ide']
INTERFACE_VIRTIO_SCSI = ENUMS['interface_virtio_scsi']

TYPE_DATA = ENUMS['storage_dom_type_data']

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

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWORD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']

NIC_TYPE_VIRTIO = ENUMS['nic_type_virtio']
TMP_CLUSTER_NAME = 'tmp_cluster'
