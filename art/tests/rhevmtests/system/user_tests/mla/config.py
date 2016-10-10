""" Test configuration - login data to the servers and test setup options.  """

from rhevmtests.system.config import *  # flake8:  noqa
from rhevmtests.system.user_tests.mla.roles import role


# Networks
NETWORK_NAMES = ["rhevm{0}".format(i) for i in range(1, 5)]

NIC_NAMES = ["nic{0}".format(i) for i in range(1, 5)]

# Users
AUTHZ = 'internal-authz'
PROFILE = 'internal'
USER_DOMAIN = AUTHZ

USER_NAMES = ["user1", "user2", "user3"]
USER_PASSWORD = '123456'

USERS = ["{0}@{1}".format(user_name, AUTHZ) for user_name in USER_NAMES]

USER1_VM_ROLES = [role.UserRole, role.PowerUserRole]
USER2_VM_ROLES = [role.TemplateAdmin]
USER1_TEMPLATE_ROLES = [
    role.UserRole,
    role.UserTemplateBasedVm,
    role.TemplateAdmin
]
USER2_TEMPLATE_ROLES = [role.TemplateOwner, role.DiskCreator]

GROUP_USER_NAME = 'user_of_group'
GROUP_USER = "{0}@{1}".format(GROUP_USER_NAME, AUTHZ)
GROUP_NAME = 'group1'

# Misc
ALT_CLUSTER_NAME = 'user_info_access__cluster'
DC_NAME_B = 'user_info_access__dc_b'
CLUSTER_NAME_B = 'user_info_access__cluster_b'

TIMEOUT = 60 * 2
HOST_INSTALL_TIMEOUT = 90 * 10

# Objects
DISK_NAME = 'users__disk'
DISK_NAME1 = 'users__disk1'
VM_NAME = "users__vm"
VM_NAMES = ["users__ia_vm{0}".format(i) for i in range(1, 5)]

VM_NO_DISK = 'users__vm_nodisk'

TEMPLATE_NAMES = ["users__template{0}".format(i) for i in range(1, 5)]

TEMPLATE_NO_DISK = 'users__template_nodisk'
VMPOOL_NAME = 'users__vmpool'
SNAPSHOT_DEF = 'Active VM'
USER_ROLE = 'users__role_user'
ADMIN_ROLE = 'users__role_admin'

MASTER_STORAGE = None