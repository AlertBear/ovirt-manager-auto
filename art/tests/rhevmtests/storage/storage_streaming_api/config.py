"""
Config module for download image
"""
from rhevmtests.storage.config import *  # flake8: noqa

TARGET_FILE_PATH = os.path.expanduser('~')
DOWNLOAD = 'download'
UPLOAD = 'upload'
IMAGE_FULL_SIZE = 0
UPLOAD_DIR_PATH = '~/upload/'
UPLOAD_FILES_LOCALHOST_PATH = [
    os.path.expanduser(
        UPLOAD_DIR_PATH + 'qcow2_v2_rhel7.4_ovirt4.2_guest_disk_1G'
    ),
    os.path.expanduser(UPLOAD_DIR_PATH + 'qcow2_v3_cow_sparse_disk_1G'),
    os.path.expanduser(UPLOAD_DIR_PATH + 'test_raw_to_delete')
]
RSYNC_CMD = '/usr/bin/rsync --ignore-existing '
REMOTE_HOST = 'yellow-vdsb.qa.lab.tlv.redhat.com'
YELLOW_PASS = 'qum10net'

UPLOAD_IMAGES_YELLOW_PATHS = [
    '/Storage_NFS/upload_images/qcow2_v2_rhel7.4_ovirt4.2_guest_disk_1G',
    '/Storage_NFS/upload_images/qcow2_v3_cow_sparse_disk_1G',
    '/Storage_NFS/upload_images/test_raw_to_delete',
]
RSYNC_TIMEOUT = 600
PEXPECT_LOG = '/tmp/pexpect_log.txt'
CA_FILE_ORIG = '/var/tmp/ca.crt'
CA_FILE = "ca.crt"
WORKSPACE_PATH = os.getenv('WORKSPACE', '~/')
CA_FILE_NEW = os.path.expanduser(os.path.join(WORKSPACE_PATH, CA_FILE))
MOVE_CERT_CMD = 'mv -f %s %s'
DISK_RESIZE_TIMEOUT = 1200
DOWNLOAD_DIR_PATH = '~/download/'
FILE_PATH = os.path.expanduser(DOWNLOAD_DIR_PATH)
