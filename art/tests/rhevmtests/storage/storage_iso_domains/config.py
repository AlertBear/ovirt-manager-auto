from rhevmtests.storage.config import *  # flake8: noqa
import hashlib
import time

__test__ = False

TESTNAME = PARAMETERS.get('basename', 'StorageIsoDomains')

REST_PASS = REST_CONNECTION['password']

ADDRESS = UNUSED_DATA_DOMAIN_ADDRESSES[:]
PATH = UNUSED_DATA_DOMAIN_PATHS[:]
LUNS = UNUSED_LUNS[:]
LUN_ADDRESS = UNUSED_LUN_ADDRESSES[:]
LUN_TARGET = UNUSED_LUN_TARGETS[:]

# TODO: Give proper values if GE is able to run on Local in the future
LOCAL_DOMAINS = [None, None]

LUN_PORT = 3260

ISO_NFS_DOMAIN = {
    'name': 'nfsIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': STORAGE_TYPE_NFS,
    'address': None,  # Filed in setup_package
    'path': None,  # Filed in setup_package
}

ISO_POSIX_DOMAIN = {
    'name': 'posixIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'address': None,  # Filed in setup_package
    'path': None,  # Filed in setup_package
    'storage_type': STORAGE_TYPE_POSIX,
    'vfs_type': STORAGE_TYPE_NFS,
    'storage_format': ENUMS['storage_format_version_v1'],
}

ISO_LOCAL_DOMAIN = {
    'name': 'localIsoDomain',
    'type': ENUMS['storage_dom_type_iso'],
    'storage_type': STORAGE_TYPE_LOCAL,
    'path': None,  # Filed in setup_package
}

LOCAL_DOMAIN = {
    'name': 'localStorageDomain',
    'type': TYPE_DATA,
    'storage_type': STORAGE_TYPE_LOCAL,
    'path': None,  # Filed in setup_package
}

ISCSI_DOMAIN = {
    'name': 'iscsiDomain',
    'type': TYPE_DATA,
    'storage_type': STORAGE_TYPE_ISCSI,
    'lun': None,  # Filed in setup_package
    'lun_address': None,  # Filed in setup_package
    'lun_target': None,  # Filed in setup_package
    'lun_port': LUN_PORT,
}


sha1 = hashlib.sha1("%f" % time.time()).hexdigest()
TARGETDIR = '/tmp/mnt%s' % sha1
MKDIR_CMD = 'mkdir %s' % TARGETDIR
RMDIR_CMD = 'rm -rf %s' % TARGETDIR
MOUNT_CMD = 'mount -t nfs %s:%s %s' % (iso_address, iso_path, TARGETDIR)
UMOUNT_CMD = 'umount %s' % TARGETDIR
