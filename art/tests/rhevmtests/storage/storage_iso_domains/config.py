from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

TESTNAME = PARAMETERS.get('basename', 'StorageIsoDomains')

REST_PASS = REST_CONNECTION['password']

if GOLDEN_ENV:
    ADDRESS = UNUSED_DATA_DOMAIN_ADDRESSES[:]
    PATH = UNUSED_DATA_DOMAIN_PATHS[:]
    LUNS = UNUSED_LUNS[:]
    LUN_ADDRESS = UNUSED_LUN_ADDRESSES[:]
    LUN_TARGET = UNUSED_LUN_TARGETS[:]

    # TODO: Give proper values if GE is able to run on Local in the future
    LOCAL_DOMAIN = [None, None]
else:
    ADDRESS = PARAMETERS.as_list('data_domain_address')
    PATH = PARAMETERS.as_list('data_domain_path')
    LUNS = PARAMETERS.as_list('lun')
    LUN_ADDRESS = PARAMETERS.as_list('lun_address')
    LUN_TARGET = PARAMETERS.as_list('lun_target')

    LOCAL_DOMAIN = PARAMETERS.as_list('local_domain_path')

LUN_PORT = 3260

ISO_NFS_DOMAIN = {
    'name': 'nfsIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': STORAGE_TYPE_NFS,
    'address': ADDRESS[0],
    'path': PATH[0],
}

ISO_POSIX_DOMAIN = {
    'name': 'posixIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'address': ADDRESS[0],
    'path': PATH[0],
    'storage_type': STORAGE_TYPE_POSIX,
    'vfs_type': STORAGE_TYPE_NFS,
    'storage_format': ENUMS['storage_format_version_v1'],
}

ISO_LOCAL_DOMAIN = {
    'name': 'localIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': STORAGE_TYPE_LOCAL,
    'path': LOCAL_DOMAIN[1],
}

LOCAL_DOMAIN = {
    'name': 'localStorageDomain',
    'type': TYPE_DATA,
    'storage_type': STORAGE_TYPE_LOCAL,
    'path': LOCAL_DOMAIN[0],
}

ISCSI_DOMAIN = {
    'name': 'iscsiDomain',
    'type': TYPE_DATA,
    'storage_type': STORAGE_TYPE_ISCSI,
    'lun': LUNS[0],
    'lun_address': LUN_ADDRESS[0],
    'lun_target': LUN_TARGET[0],
    'lun_port': LUN_PORT,
}
