from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

TESTNAME = PARAMETERS.get('basename', 'DCMixedTypeTest')

NFS_DOMAIN = {
    'name': "nfs_0_mixed",
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': STORAGE_TYPE_NFS,
}

EXPORT_DOMAIN = {
    'name': EXPORT_DOMAIN_NAME,
    'type': ENUMS['storage_dom_type_export'],
    'storage_type': ENUMS['storage_type_nfs'],
    'path': PARAMETERS.get('export_domain_path'),
    'address': PARAMETERS.get('export_domain_address'),
}

ISCSI_DOMAIN_0 = {
    'name': 'iscsi_0_mixed',
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_iscsi'],
    'lun_port': LUN_PORT,
}

ISCSI_DOMAIN_1 = {
    'name': 'iscsi_1_mixed',
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': ENUMS['storage_type_iscsi'],
    'lun_port': LUN_PORT,
}

GLUSTER_DOMAIN = {
    'name': 'gluster_0_mixed',
    'type': ENUMS['storage_dom_type_data'],
    'storage_type': STORAGE_TYPE_GLUSTER,
    'vfs_type': ENUMS['vfs_type_glusterfs'],
}

FC_DOMAIN = {
    'name': 'fc_domain',
}

if not GOLDEN_ENV:
    NFS_DOMAIN.update({
        'address': ADDRESS[0],
        'path': PATH[0],
    })
    ISCSI_DOMAIN_0.update({
        'lun': LUN[0],
        'lun_address': LUN_ADDRESS[0],
        'lun_target': LUN_TARGET[0],
    })
    ISCSI_DOMAIN_1.update({
        'lun': LUN[1],
        'lun_address': LUN_ADDRESS[1],
        'lun_target': LUN_TARGET[1],
    })
    GLUSTER_DOMAIN.update({
        'address': GLUSTER_ADDRESS[0],
        'path': GLUSTER_PATH[0],
    })
else:
    NFS_DOMAIN.update({
        'address': UNUSED_DATA_DOMAIN_ADDRESSES[0],
        'path': UNUSED_DATA_DOMAIN_PATHS[0],
    })
    ISCSI_DOMAIN_0.update({
        'lun': UNUSED_LUNS[0],
        'lun_address': UNUSED_LUN_ADDRESSES[0],
        'lun_target': UNUSED_LUN_TARGETS[0],
    })
    ISCSI_DOMAIN_1.update({
        'lun': UNUSED_LUNS[1],
        'lun_address': UNUSED_LUN_ADDRESSES[1],
        'lun_target': UNUSED_LUN_TARGETS[1],
    })
    GLUSTER_DOMAIN.update({
        'address': UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
        'path': UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0],
    })

POSIX_DOMAIN = NFS_DOMAIN.copy()
POSIX_DOMAIN['storage_type'] = STORAGE_TYPE_POSIX
POSIX_DOMAIN['vfs_type'] = STORAGE_TYPE_NFS
