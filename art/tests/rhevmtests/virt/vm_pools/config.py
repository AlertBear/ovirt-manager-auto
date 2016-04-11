"""
Vm Pool test config
"""
from rhevmtests.virt.config import *  # flake8:  noqa

MISSING_PRESTARTED_MSG = "VmPool '%s' is missing %s prestarted Vms"
NO_AVAILABLE_VMS_MSG = "No Vms avaialable for prestarting"
ALLOCATE_VM_POSITIVE_MSG = "Failed to take a vm from pool: %s as user: %s"
ALLOCATE_VM_NEGETIVE_MSG = (
    "Allocating a vm from pool %s as user: %s was successful although expected "
    "to fail"
)
TIME_PATTERN = "[0-2][0-9]:[0-5][0-9]"
NEW_IMPLEMENTATION_VERSION = '4.0'
PRESTARTED_VMS_TIMEOUT = 90
VM_POOL_ACTION_TIMEOUT = 300
VM_POOL_ACTION_SLEEP = 5
INTERNAL_DOMAIN = 'internal'
USER_DOMAIN = "%s-authz" % INTERNAL_DOMAIN
USER = 'user1'
USER_PASSWORD = '123456'
USER_ROLE = ENUMS['role_name_user_role']
FILE_NAME = 'test_file'
TEMP_PATH = '/var/tmp/'

