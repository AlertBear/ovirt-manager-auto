"""
Config module for storage backup restore api
"""

__test__ = False

from art.rhevm_api.utils import test_utils
from . import ART_CONFIG
from art.test_handler.settings import opts


ENUMS = opts['elements_conf']['RHEVM Enums']


# Name of the test
TESTNAME = "storage_backup_restore_api"

PARAMETERS = ART_CONFIG['PARAMETERS']

# DC info
LOCAL = PARAMETERS['local']
STORAGE_TYPE = PARAMETERS['storage_type']

STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']

# Data-center name
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)
if STORAGE_TYPE == STORAGE_TYPE_NFS:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')
    LUN_PORT = 3260

# Cluster name
CLUSTER_NAME = 'cluster_%s' % TESTNAME

# Storage domain names
SD_NAME = "%s_0" % STORAGE_TYPE
SD_NAME_1 = "%s_1" % STORAGE_TYPE


OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

VM_COUNT = 2

VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

VM_PAUSED = ENUMS['vm_state_paused']
VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

HOSTS = PARAMETERS.as_list('vds')
VDS_PASSWORD = PARAMETERS.as_list('vds_password')
VDS_USER = PARAMETERS.as_list('vds_admin')

DISK_INTERFACE_VIRTIO = ENUMS['interface_virtio']
VOLUME_FORMAT_COW = ENUMS['format_cow']
SPARSE = True

DISK_INTERFACES = (ENUMS['interface_ide'], ENUMS['interface_virtio'])
DISK_FORMATS = (ENUMS['format_raw'], ENUMS['format_cow'])
