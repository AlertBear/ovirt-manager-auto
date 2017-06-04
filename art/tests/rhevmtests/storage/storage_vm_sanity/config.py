"""
Config module for storage vm sanity
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "storage_vm_sanity"

TEMPLATE_NAME = 'template_name'

# TODO: remove
VM_LINUX_USER = VMS_LINUX_USER
VM_LINUX_PASSWORD = VMS_LINUX_PW

REGEX = 'createVolume'
EXTENT_SIZE = 128 * MB
REMOVE_TEMPLATE_TIMEOUT = 300
LOG_LISTENER_TIMEOUT = 60
