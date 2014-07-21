from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

TESTNAME = PARAMETERS.get('basename', 'StorageIsoDomains')

# TODO: remove
REST_PASS = VDC_PASSWORD
VDC_USER = VDC_ROOT_USER

# TODO: remove
HOST = HOSTS[0]
HOST_ADMIN = HOSTS_USER
HOST_PASSWORD = HOSTS_PW

# TODO: remove
VIRTIO_SCSI = INTERFACE_VIRTIO_SCSI

# TODO: remove this
ISCSI_SD_TYPE = STORAGE_TYPE_ISCSI
NFS_SD_TYPE = STORAGE_TYPE_NFS

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
