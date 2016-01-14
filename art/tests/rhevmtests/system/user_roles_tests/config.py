""" Test configuration - login data to the servers and test setup options.  """
__test__ = False

from rhevmtests.system.config import *  # flake8:  noqa

# Networks
NETWORK_NAME = MGMT_BRIDGE
NETWORK_NAME1 = 'rhevm1'
NETWORK_NAME2 = 'rhevm2'
NETWORK_NAME3 = 'rhevm3'
NETWORK_NAME4 = 'rhevm4'

# Users
AUTHZ = 'internal-authz'
PROFILE = 'internal'
USER_DOMAIN = AUTHZ

USER_NAME = 'user1'
USER_NAME2 = 'user2'
USER_NAME3 = 'user3'
USER_PASSWORD = '123456'

USER1 = 'user1@%s' % AUTHZ
USER2 = 'user2@%s' % AUTHZ
USER3 = 'user3@%s' % AUTHZ
USER = USER1

GROUP_USER = 'user_of_group'
GROUP_NAME = 'group1'

# Misc
ALT_CLUSTER_NAME = 'user_info_access__cluster'
DC_NAME_B = 'user_info_access__dc_b'
CLUSTER_NAME_B = 'user_info_access__cluster_b'

TIMEOUT = 60*2
HOST_INSTALL_TIMEOUT = 90*10

# Objects
DISK_NAME = 'users__disk'
DISK_NAME1 = 'users__disk1'
VM_NAME = "users__vm"
VM_NAME1 = "users__ia_vm1"
VM_NAME2 = "users__ia_vm2"
VM_NAME3 = "users__ia_vm3"
VM_NAME4 = "users__ia_vm4"
VM_NO_DISK = 'users__vm_nodisk'
TEMPLATE_NAME1 = 'users__template'
TEMPLATE_NAME2 = 'users__template2'
TEMPLATE_NAME3 = 'users__template3'
TEMPLATE_NAME4 = 'users__template4'
TEMPLATE_NO_DISK = 'users__template_nodisk'
VMPOOL_NAME = 'users__vmpool'
SNAPSHOT_DEF = 'Active VM'
USER_ROLE = 'users__role_user'
ADMIN_ROLE = 'users__role_admin'
