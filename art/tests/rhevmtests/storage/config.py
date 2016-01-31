"""
Storage related global config file
"""
from rhevmtests.config import *  # flake8: noqa

__test__ = False

TESTNAME = "GlobalStorage"
DATA_CENTER_NAME = DC_NAME[0]
CLUSTER_NAME = CLUSTER_NAME[0]
GLANCE_IMAGE_COW = 'cow_sparse_disk'
GLANCE_IMAGE_RAW = 'raw_preallocated_disk'
# CLUSTER SECTION
COMPATIBILITY_VERSION = COMP_VERSION

# VDC/ENGINE section
VDC = VDC_HOST
VDC_PASSWORD = VDC_ROOT_PASSWORD

VM_DISK_SIZE = 6 * GB
DISK_SIZE = 1 * GB

VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

NUMBER_OF_DISKS = int(PARAMETERS.get('no_of_disks', 8))

STORAGES_MATRIX = opts['storages']

# Storage domain names
STORAGE_DEVICE_TYPE_MAP = {
    STORAGE_TYPE_POSIX: STORAGE_TYPE_NFS,  # posix   -> nfs_devices
    STORAGE_TYPE_LOCAL: "local",           # localfs -> local_devices
    STORAGE_TYPE_GLUSTER: "gluster",       # glusterfs -> gluster_devices
}

STORAGE_DEVICE_NAME = STORAGE_DEVICE_TYPE_MAP.get(STORAGE_TYPE, STORAGE_TYPE)

if not GOLDEN_ENV:
    if STORAGE_TYPE == STORAGE_TYPE_LOCAL:
        # defined in conf as list of directories
        NUMBER_OF_SDS = len(
            STORAGE_CONF.as_list('%s_devices' % STORAGE_DEVICE_NAME))

    elif STORAGE_TYPE == "none":
        # There are a few tests that uses multiple types of storage and
        # STORAGE_TYPE is none
        NUMBER_OF_SDS = 0

    elif STORAGE_TYPE:
        NUMBER_OF_SDS = int(STORAGE_CONF.get('%s_devices' %
                                             STORAGE_DEVICE_NAME))
    STORAGE_SELECTOR = [STORAGE_TYPE]
else:
    # XXX WA until the multi selector plugin is merge
    # Get the list of sds that would the test run with testmultiplier
    STORAGE_SELECTOR = STORAGES_MATRIX
    STORAGE_TYPE = 'golden_env'
    NUMBER_OF_SDS = 3

SD_NAMES_LIST = []
for idx in range(NUMBER_OF_SDS):
    sd_name = '%s_%s' % (STORAGE_TYPE, idx)
    SD_NAMES_LIST.append(sd_name)
    globals()["SD_NAME_%d" % idx] = sd_name

DISK_INTERFACE_VIRTIO = INTERFACE_VIRTIO
VOLUME_FORMAT_COW = DISK_FORMAT_COW
SPARSE = True

VM_LOCK_STATE = VM_LOCKED
VM_DOWN_STATE = VM_DOWN

EXTEND_LUN = PARAMETERS.get('extend_lun', None)

SD_STATE_ACTIVE = SD_ACTIVE

DC_TYPE = PARAMETERS['storage_type']

SETUP_ADDRESS = VDC

FIRST_HOST = None  # Filled in setup_package

# TODO - move to test
TYPE_DATA = ENUMS['storage_dom_type_data']
TYPE_IMAGE = ENUMS['storage_dom_type_image']

TMP_CLUSTER_NAME = 'tmp_cluster'

SETUP_PASSWORD = VDC_ROOT_PASSWORD

DATA_ROOT_DIR = PARAMETERS.get('data_root_dir', "/tmp/snapshotTest")
DATA_DIR_CNT = PARAMETERS.get('data_dir_cnt', 5)
DATA_FILE_CNT = PARAMETERS.get('data_file_cnt', 12)
DEST_DIR = PARAMETERS.get('dest_dir', "/tmp")

VIRTIO_SCSI = INTERFACE_VIRTIO_SCSI
VIRTIO_BLK = INTERFACE_VIRTIO
IDE = INTERFACE_IDE

COW_DISK = DISK_FORMAT_COW
RAW_DISK = DISK_FORMAT_RAW

VM_BASE_NAME = "storage_vm"
DISK_NAME_FORMAT = "%s_%s_%s_disk"

# TODO: What is this?
STORAGE_SECTION = ART_CONFIG['STORAGE']

WAIT_TIME = 120

BLOCK_TYPES = [STORAGE_TYPE_ISCSI, STORAGE_TYPE_FCP]
BLOCK_FS = STORAGE_TYPE in BLOCK_TYPES

ISO_UPLOADER_CONF_FILE = "/etc/ovirt-engine/isouploader.conf"
ISO_IMAGE = PARAMETERS.get('cdrom_image')

iso_address = ISO_DOMAIN_ADDRESS
iso_path = ISO_DOMAIN_PATH

LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']
OVF_DISK_ALIAS = ENUMS['ovf_disk_alias']

# disk interfaces
VIRTIO = INTERFACE_VIRTIO

# Snapshot actions
PREVIEW = ENUMS['preview_snapshot']
UNDO = ENUMS['undo_snapshot']
COMMIT = ENUMS['commit_snapshot']

HOST_NONOPERATIONAL = ENUMS['search_host_state_non_operational']

HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]

VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']

# These lists of keywords are useful for low_level addStorageDomain:
# addStorageDomain(True, name='my_name', **NFS_DOMAINS_KWARGS[0])
NFS_DOMAINS_KWARGS = [
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': STORAGE_TYPE_NFS,
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': STORAGE_TYPE_NFS,
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': STORAGE_TYPE_NFS,
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
]

ISCSI_DOMAINS_KWARGS = [
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_iscsi'],
        'lun_port': LUN_PORT,
        'lun_address': None,  # Filled in setup_package
        'lun_target': None,  # Filled in setup_package
        'lun': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_iscsi'],
        'lun_port': LUN_PORT,
        'lun_address': None,  # Filled in setup_package
        'lun_target': None,  # Filled in setup_package
        'lun': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_iscsi'],
        'lun_port': LUN_PORT,
        'lun_address': None,  # Filled in setup_package
        'lun_target': None,  # Filled in setup_package
        'lun': None,  # Filled in setup_package
    },
]

GLUSTER_DOMAINS_KWARGS = [
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': STORAGE_TYPE_GLUSTER,
        'vfs_type': ENUMS['vfs_type_glusterfs'],
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'vfs_type': ENUMS['vfs_type_glusterfs'],
        'storage_type': STORAGE_TYPE_GLUSTER,
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'vfs_type': ENUMS['vfs_type_glusterfs'],
        'storage_type': STORAGE_TYPE_GLUSTER,
        'address': None,  # Filled in setup_package
        'path': None,  # Filled in setup_package
    },
]

# addStorageDomain(True, name='my_name', **STORAGE_DOMAINS_KWARGS['nfs'][0])
STORAGE_DOMAINS_KWARGS = {
    STORAGE_TYPE_NFS: NFS_DOMAINS_KWARGS,
    STORAGE_TYPE_ISCSI: ISCSI_DOMAINS_KWARGS,
    STORAGE_TYPE_GLUSTER: GLUSTER_DOMAINS_KWARGS,
}

disk_args = {
    'provisioned_size': DISK_SIZE,
    'wipe_after_delete': BLOCK_FS,
    'storagedomain': None,
    'bootable': False,
    'shareable': False,
    'active': True,
    'interface': VIRTIO,
    'format': COW_DISK,
    'sparse': True,
    'alias': '',
    'description': '',
}
create_vm_args = {
    'positive': True,
    'vmName': '',
    'vmDescription': '',
    'storageDomainName': None,
    'cluster': CLUSTER_NAME,
    'nic': NIC_NAME[0],
    'nicType': NIC_TYPE_VIRTIO,
    'size': VM_DISK_SIZE,
    'diskInterface': INTERFACE_VIRTIO,
    'volumeFormat': DISK_FORMAT_COW,
    'volumeType': True,  # sparse
    'bootable': True,
    'type': VM_TYPE_DESKTOP,
    'os_type': OS_TYPE,
    'memory': GB,
    'cpu_socket': CPU_SOCKET,
    'cpu_cores': CPU_CORES,
    'display_type': DISPLAY_TYPE,
    'start': 'false',
    'installation': True,
    'user': COBBLER_USER,
    'password': COBBLER_PASSWD,
    'image': COBBLER_PROFILE,
    'network': MGMT_BRIDGE,
    'useAgent': USE_AGENT,
}
clone_vm_args = {
    'positive': True,
    'name': '',
    'vmDescription': '',
    'cluster': CLUSTER_NAME,
    'template': TEMPLATE_NAME[0],
    'clone': False,
    'vol_sparse': True,
    'vol_format': COW_DISK,
    'storagedomain': None,
    'virtio_scsi': True,
    'display_type': DISPLAY_TYPE,
    'os_type': OS_TYPE,
    'type': VM_TYPE,
    'placement_host': None,
    'placement_affinity': None,
    'highly_available': None,
}
