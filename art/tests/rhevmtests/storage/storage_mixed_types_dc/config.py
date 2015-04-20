from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

# Name of the test
TESTNAME = PARAMETERS.get('basename', 'DCMixedTypeTest')

# TODO: Remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

# TODO: remove
HOST = HOSTS[0]
HOST_ADMIN = HOSTS_USER
HOST_PASSWORD = HOSTS_PW

FC_SD_NAME_1 = "fc_sd"
ISCSI_SD_NAME_1 = "iscsi_sd"
ISCSI_SD_NAME_2 = "iscsi_sd2"
NFS_SD_NAME_1 = "nfs_sd"
GLUSTER_SD_NAME_1 = "gluster"

if not GOLDEN_ENV:
    NFS_DOMAIN = {
        'name': NFS_SD_NAME_1,
        'type': ENUMS['storage_dom_type_data'],
        'address': ADDRESS[0],
        'storage_type': STORAGE_TYPE_NFS,
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
        'storage_type': STORAGE_TYPE_GLUSTER,
        'address': GLUSTER_ADDRESS[1],
        'path': GLUSTER_PATH[1],
        'vfs_type': ENUMS['vfs_type_glusterfs'],
    }

    FC_DOMAIN = {
        'name': 'fc_domain',
    }

    POSIX_DOMAIN = NFS_DOMAIN.copy()
    POSIX_DOMAIN['storage_type'] = STORAGE_TYPE_POSIX
    POSIX_DOMAIN['vfs_type'] = STORAGE_TYPE_NFS
else:
    NFS_DOMAIN = {'name': ''}
    ISCSI_DOMAIN = {'name': ''}
    ISCSI_DOMAIN2 = {'name': ''}
    POSIX_DOMAIN = {'name': ''}
    FC_DOMAIN = {'name': ''}
    GLUSTER_DOMAIN = {'name': ''}
    EXPORT_DOMAIN = {'name': ''}
