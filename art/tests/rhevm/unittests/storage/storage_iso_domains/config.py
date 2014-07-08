from art.test_handler.settings import ART_CONFIG
from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']

# Name of the test
TESTNAME = PARAMETERS.get('basename', 'StorageIsoDomains')

ENUMS = opts['elements_conf']['RHEVM Enums']

VDC = PARAMETERS.get('host', None)
VDC_USER = "root"
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
REST_PASS = ART_CONFIG['REST_CONNECTION'].get("password")

STORAGE_TYPE = PARAMETERS['storage_type']
DATA_CENTER_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TESTNAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TESTNAME)

if STORAGE_TYPE.startswith(ENUMS['storage_type_posixfs']):
    STORAGE_TYPE = (PARAMETERS['storage_type']).split("_")[0]
    PARAMETERS['storage_type'] = STORAGE_TYPE

HOST = PARAMETERS.as_list('vds')[0]
HOST_ADMIN = PARAMETERS.as_list('vds_admin')[0]
HOST_PASSWORD = PARAMETERS.as_list('vds_password')[0]

DISK_SIZE = 4 * GB
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']
DISK_FORMAT_COW = ENUMS['format_cow']
DISK_TYPE_SYSTEM = ENUMS['disk_type_system']
CPU_SOCKET = PARAMETERS.get('cpu_socket', 2)
CPU_CORES = PARAMETERS.get('cpu_cores', 2)
OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']
VM_TYPE_DESKTOP = ENUMS['vm_type_desktop']

VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']

ISCSI_SD_TYPE = ENUMS['storage_type_iscsi']
NFS_SD_TYPE = ENUMS['storage_type_nfs']

PATH = PARAMETERS.as_list('data_domain_path')
ADDRESS = PARAMETERS.as_list('data_domain_address')

LUN = PARAMETERS.as_list('lun')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_PORT = 3260

ISO_UPLOADER_CONF_FILE = "/etc/ovirt-engine/isouploader.conf"
ISO_IMAGE = PARAMETERS.get('cdrom_image')

iso_address = PARAMETERS.get("shared_iso_domain_address")
iso_path = PARAMETERS.get("shared_iso_domain_path")

ISO_NFS_DOMAIN = {
    "name": "nfsIsoDomain",
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': ENUMS['storage_type_nfs'],
    'address': ADDRESS[0],
    'path': PATH[0],
}

ISO_POSIX_DOMAIN = {
    "name": "posixIsoDomain",
    'type': ENUMS['storage_dom_type_iso'],
    'address': ADDRESS[0],
    'path': PATH[0],
    'storage_type': ENUMS['storage_type_posixfs'],
    'vfs_type': NFS_SD_TYPE,
    'storage_format': ENUMS['storage_format_version_v1'],
}

ISO_LOCAL_DOMAIN = {
    "name": "localIsoDomain",
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': ENUMS['storage_type_local'],
    'path': PARAMETERS.as_list("local_domain_path")[1],
}

ISCSI_DOMAIN = {
    'name': "iscsiDomain",
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_iscsi'],
    'lun': LUN[0],
    'lun_address': LUN_ADDRESS[0],
    'lun_target': LUN_TARGET[0],
    'lun_port': LUN_PORT,
}

LOCAL_DOMAIN = {
    'name': "localStorageDomain",
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_local'],
    'path': PARAMETERS.as_list("local_domain_path")[0],
}
