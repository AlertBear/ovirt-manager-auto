"""
Config module for full snapshot test
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "storage_snapshot_full"

# TODO: remove
BASE_SNAPSHOT = 'clean_os_base_snapshot'
EXPORT_DOMAIN = EXPORT_DOMAIN_NAME

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW
RAM_SNAPSHOT = 'ram_snapshot_%s'

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD

MAX_DESC_LENGTH = 4000
SPECIAL_CHAR_DESC = '!@#$\% ^&*/\\'
