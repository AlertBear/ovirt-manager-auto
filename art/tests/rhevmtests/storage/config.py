"""
Storage related global config file
"""
from rhevmtests.config import *  # flake8: noqa

__test__ = False

TESTNAME = "GlobalStorage"
DATA_CENTER_NAME = DC_NAME[0]
CLUSTER_NAME = CLUSTER_NAME[0]
EXPORT_DOMAIN_NAME = PARAMETERS.get('export_domain_name', 'export_domain')

# CLUSTER SECTION
COMPATIBILITY_VERSION = COMP_VERSION

# VDC/ENGINE section
VDC = VDC_HOST
VDC_PASSWORD = VDC_ROOT_PASSWORD


DISK_SIZE = int(PARAMETERS.setdefault('disk_size', 10737418240))

VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

NUMBER_OF_DISKS = int(PARAMETERS.get('no_of_disks', 8))

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
        NUMBER_OF_SDS = int(STORAGE_CONF.get('%s_devices' % STORAGE_DEVICE_NAME))
    STORAGE_SELECTOR = [STORAGE_TYPE]
else:
    # XXX WA until the multi selector plugin is merge
    # Get the list of sds that would the test run with testmultiplier
    STORAGE_SELECTOR =  [STORAGE_TYPE_ISCSI]
    STORAGE_TYPE = STORAGE_TYPE_ISCSI
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

FIRST_HOST = HOSTS[0]

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
