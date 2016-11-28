"""
Vm Pool test config
"""
from rhevmtests.virt.config import *  # flake8:  noqa

MISSING_PRESTARTED_MSG = "VmPool '%s' is missing %s prestarted VMs"
NO_AVAILABLE_VMS_MSG = "No VMs available for prestarting"
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
USER_NAME = '%s@%s' % (USER, USER_DOMAIN)
ADMIN_USER_NAME = '%s@%s' % (VDC_ADMIN_USER, USER_DOMAIN)
USER_PASSWORD = '123456'
USER_ROLE = ENUMS['role_name_user_role']
FILE_NAME = 'test_file'
TEMP_PATH = '/var/tmp/'

VM_POOLS_PARAMS = {
    'size': 2,
    'cluster': CLUSTER_NAME[0],
    'template': TEMPLATE_NAME[0],
    'max_user_vms': 1,
    'prestarted_vms': 0,
    'type_': 'automatic',
}
MAX_VMS_IN_POOL_TEST = 20
MAC_POOL_SIZE = 60
