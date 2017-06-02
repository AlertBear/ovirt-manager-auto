"""
Storage related global config file
"""
from rhevmtests.config import *  # flake8: noqa

__test__ = False

TESTNAME = "GlobalStorage"
CLUSTER_NAME = CLUSTER_NAME[0]
GLANCE_IMAGE_COW = 'cow_sparse_disk'
GLANCE_IMAGE_RAW = 'raw_preallocated_disk'
# CLUSTER SECTION
COMPATIBILITY_VERSION = COMP_VERSION

# VDC/ENGINE section
VDC = VDC_HOST
VDC_PASSWORD = VDC_ROOT_PASSWORD

# SPM priority parameters
DEFAULT_SPM_PRIORITY = 5
LOW_SPM_PRIORITY = 1

TIMEOUT_DEACTIVATE_DOMAIN = 90

VM_DISK_SIZE = 6 * GB
DISK_SIZE = 1 * GB

# posix backend supported types
POSIX_BACKENDS = [STORAGE_TYPE_NFS, STORAGE_TYPE_CEPH]

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
TYPE_ISO = ENUMS['storage_dom_type_iso']
TYPE_EXPORT = ENUMS['storage_dom_type_export']

TMP_CLUSTER_NAME = 'tmp_cluster'

ROOT_PASSWORD = VDC_ROOT_PASSWORD

DATA_ROOT_DIR = PARAMETERS.get('data_root_dir', "/tmp/snapshotTest")
DATA_DIR_CNT = PARAMETERS.get('data_dir_cnt', 5)
DATA_FILE_CNT = PARAMETERS.get('data_file_cnt', 12)
DEST_DIR = PARAMETERS.get('dest_dir', "/tmp")

VIRTIO_SCSI = INTERFACE_VIRTIO_SCSI
VIRTIO_BLK = INTERFACE_VIRTIO
IDE = INTERFACE_IDE

BLANK_TEMPLATE_ID = "00000000-0000-0000-0000-000000000000"

COW_DISK = DISK_FORMAT_COW
RAW_DISK = DISK_FORMAT_RAW

QCOW_V3 = DISK_QCOW_V3
QCOW_V2 = DISK_QCOW_V2

KILL_VDSM = "kill `systemctl show vdsmd -p MainPID | awk -F '=' {'print $2'}`"
RESTART_ENGINE = "systemctl restart ovirt-engine.service"

MD5SUM_CMD = "md5sum %s"
TEXT_CONTENT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
    "sed do eiusmod tempor incididunt ut labore et dolore magna "
    "aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
    "ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit "
    "esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
    "occaecat cupidatat non proident, sunt in culpa qui officia "
    "deserunt mollit anim id est laborum."
)

SYNC_CMD = 'sync'

VM_BASE_NAME = "storage_vm"
DISK_NAME_FORMAT = "%s_%s_%s_disk"

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
ACTIVE_SNAPSHOT = 'Active VM'

HOST_NONOPERATIONAL = ENUMS['search_host_state_non_operational']

HOST_NONRESPONSIVE = ENUMS["search_host_state_non_responsive"]

VM_PINNED = ENUMS['vm_affinity_pinned']
VM_ANY_HOST = ENUMS['vm_affinity_migratable']

OBJECT_TYPE_CLUSTER = "cl"
OBJECT_TYPE_DC = "dc"
OBJECT_TYPE_DISK = "disk"
OBJECT_TYPE_DIRECT_LUN = "direct_lun"
OBJECT_TYPE_POOL = "pool"
OBJECT_TYPE_SD = "sd"
OBJECT_TYPE_SNAPSHOT = "snap"
OBJECT_TYPE_TEMPLATE = "templ"
OBJECT_TYPE_VM = "vm"
OBJECT_TYPE_MOUNT_POINT = "mount_point"
OBJECT_TYPE_NIC = "nic"

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

FC_DOMAINS_KWARGS = [
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_fcp'],
        'fc_lun': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_fcp'],
        'fc_lun': None,  # Filled in setup_package
    },
    {
        'type': ENUMS['storage_dom_type_data'],
        'storage_type': ENUMS['storage_type_fcp'],
        'fc_lun': None,  # Filled in setup_package
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
attach_disk_params = {
    'active': True,
    'read_only': False,
    'interface': VIRTIO,
    'bootable': False,
}
create_vm_args = {
    'positive': True,
    'vmName': '',
    'vmDescription': '',
    'storageDomainName': None,
    'cluster': CLUSTER_NAME,
    'nic': NIC_NAME[0],
    'nicType': NIC_TYPE_VIRTIO,
    'provisioned_size': VM_DISK_SIZE,
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

GLUSTER_REPLICA_PATH = PARAMETERS.get('gluster_replica_path', None)
GLUSTER_REPLICA_SERVERS = get_list(PARAMETERS, 'gluster_replica_servers')

REGEX_DD_WIPE_AFTER_DELETE = 'dd.* if=/dev/zero.* of=.*/%s'

DEV_ZERO = '/dev/zero'
DEV_URANDOM = '/dev/urandom'
MOUNT_POINT = None

MASTER_DOMAIN = None
MOUNT_POINTS = dict()

# HSM Verbs
COPY_VOLUME_VERB = 'Copying Volume'

CHECKSUM_FILES = dict()

# Dictionary which contain vm_name as keys of each VM, the value is
# another dictionary that holds the VM mount points, disks ids and vm executor
# under the keys: 'disks', 'mount_points', 'executor'
DISKS_MOUNTS_EXECUTOR = dict()
FILE_NAME = 'test_file'
