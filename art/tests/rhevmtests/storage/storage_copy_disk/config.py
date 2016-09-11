"""
Config module for storage copy disk
"""
from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "copy_disk"
VM_NAME = TESTNAME + "_vm_%s"
TEST_FILE_TEMPLATE = 'test_file_copy_disk'

VM_NAMES = dict()
MOUNT_POINTS = list()
DISKS_FOR_TEST = list()
FLOATING_DISKS = list()
DISKS_BEFORE_COPY = list()
CHECKSUM_FILES = dict()
VMS_TO_REMOVE = list()
