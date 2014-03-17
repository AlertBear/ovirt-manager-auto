from . import ART_CONFIG
from art.test_handler.settings import opts

__test__ = False

GB = 1024 ** 3

PARAMETERS = ART_CONFIG['PARAMETERS']

# Name of the test
TESTNAME = PARAMETERS.get('basename', 'DCMixedTypeTest')

ENUMS = opts['elements_conf']['RHEVM Enums']
SD_ACTIVE = ENUMS['storage_domain_state_active']

VM_UP = ENUMS['vm_state_up']
VM_DOWN = ENUMS['vm_state_down']

HOST_UP = ENUMS['host_state_up']
SNAPSHOT_OK = ENUMS['snapshot_state_ok']

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

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

VM_USER = PARAMETERS.get('vm_linux_user')
VM_PASSWORD = PARAMETERS.get('vm_linux_password')

# Cobbler info
COBBLER_ADDRESS = PARAMETERS.get('cobbler_address', None)
COBBLER_PASSWD = PARAMETERS.get('cobbler_passwd', None)
COBBLER_USER = PARAMETERS.get('cobbler_user', None)
COBBLER_PROFILE = PARAMETERS['cobbler_profile']

IDE = ENUMS['interface_ide']
VIRTIO = ENUMS['interface_virtio']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']

MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

DISK_FORMAT_COW = ENUMS['format_cow']
DISK_FORMAT_RAW = ENUMS['format_raw']

FC_SD_TYPE = ENUMS['storage_type_fcp']
ISCSI_SD_TYPE = ENUMS['storage_type_iscsi']
NFS_SD_TYPE = ENUMS['storage_type_nfs']

FC_SD_NAME_1 = "fc_sd"
ISCSI_SD_NAME_1 = "iscsi_sd"
ISCSI_SD_NAME_2 = "iscsi_sd2"
NFS_SD_NAME_1 = "nfs_sd"
GLUSTER_SD_NAME_1 = "gluster"

PATH = PARAMETERS.as_list('data_domain_path')
ADDRESS = PARAMETERS.as_list('data_domain_address')

LUN = PARAMETERS.as_list('lun')
LUN_ADDRESS = PARAMETERS.as_list('lun_address')
LUN_TARGET = PARAMETERS.as_list('lun_target')
LUN_PORT = 3260

EXPORT_DOMAIN_NAME = PARAMETERS.get('export_domain_name', 'export_domain')

NFS_DOMAIN = {
    'name': NFS_SD_NAME_1,
    'type': ENUMS['storage_dom_type_data'],
    'address': ADDRESS[0],
    'storage_type': NFS_SD_TYPE,
    'path': PATH[0],
}

EXPORT_DOMAIN = {
    'name': EXPORT_DOMAIN_NAME,
    'type': ENUMS['storage_dom_type_export'],
    'storage_type': ENUMS['storage_type_nfs'],
    'path': PARAMETERS.get('export_domain_path'),
    'address': PARAMETERS.get('export_domain_address'),
}

ISCSI_DOMAIN = {
    'name': ISCSI_SD_NAME_1,
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_iscsi'],
    'lun': LUN[0],
    'lun_address': LUN_ADDRESS[0],
    'lun_target': LUN_TARGET[0],
    'lun_port': LUN_PORT,
}

ISCSI_DOMAIN2 = {
    'name': ISCSI_SD_NAME_2,
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_iscsi'],
    'lun': LUN[1],
    'lun_address': LUN_ADDRESS[1],
    'lun_target': LUN_TARGET[1],
    'lun_port': LUN_PORT,
}

GLUSTER_DOMAIN = {
    'name': GLUSTER_SD_NAME_1,
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_gluster'],
    'address': ADDRESS[1],
    'path': PATH[1],
    'vfs_type': ENUMS['vfs_type_glusterfs'],
}

FC_DOMAIN = {
    'name': 'fc_domain',
}

POSIX_DOMAIN = NFS_DOMAIN.copy()
POSIX_DOMAIN['storage_type'] = ENUMS['storage_type_posixfs']
POSIX_DOMAIN['vfs_type'] = NFS_SD_TYPE
