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

POSIX_DOMAIN = NFS_DOMAIN.copy()
POSIX_DOMAIN['storage_type'] = STORAGE_TYPE_POSIX
POSIX_DOMAIN['vfs_type'] = STORAGE_TYPE_NFS
