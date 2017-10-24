
from rhevmtests.compute.virt.config import *  # flake8: noqa

COPY_MOVE_DISK_TIMEOUT = 600
THIN_PROVISIONED_VMS = []
SPARSIFY_VM_NAME = 'sparsify_test'
PREALLOCATED_VMS = []
FILE_SIZE_IN_MB = 400
THIN_VM_PARAMS = {
    'clone': False,
    'vol_sparse': True,
    'format': DISK_FORMAT_COW,
}
PREALLOCATED_VM_PARAMS = {
    'clone': True,
    'vol_sparse': False,
    'vol_format': DISK_FORMAT_RAW,
}
DIRECT_LUN_ALIAS = 'virt_direct_lun_disk'
DIRECT_LUN_KWARGS = {
    "interface": INTERFACE_VIRTIO_SCSI,
    "alias": DIRECT_LUN_ALIAS,
    "type_": STORAGE_TYPE_ISCSI,
    "lun_address": LUN_ADDRESSES[0] if LUN_ADDRESSES else None,
    "lun_target": LUN_TARGETS[0] if LUN_TARGETS else None,
    "lun_id": LUNS[0] if LUNS else None,
}
NEW_LUN = 'sparsify_test_lun'
NEW_LUN_SIZE = 50
NEW_SD_NAME = "sparsify_test_%s_domain"
NEW_SD = None
NEW_DISKS_ALIAS = ["new_disk_sparsify_test_%s" % i for i in range(1, 3)]
RUNNING_HOST = None
RUNNING_HOST_RESOURCE = None
COPY_DISK_TIMEOUT = 900
NFS_VERSION_AUTO = 'auto'
NFS_VERSION_4_2 = '4.2'
