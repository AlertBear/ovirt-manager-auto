""" Test configuration - login data to the servers and test setup options.  """
__test__ = False

from rhevmtests.system.config import *  # flake8:  noqa

# Networks
NETWORK_NAME = 'rhevm'
NETWORK_NAME1 = 'rhevm1'
NETWORK_NAME2 = 'rhevm2'
NETWORK_NAME3 = 'rhevm3'
NETWORK_NAME4 = 'rhevm4'

# Users
USER_NAME = 'userportal1'
USER_NAME2 = 'userportal2'
USER_NAME3 = 'userportal3'
USER_DOMAIN = 'qa.lab.tlv.redhat.com'
USER_PASSWORD = '123456'

USER1 = 'userportal1@qa.lab.tlv.redhat.com'
USER2 = 'userportal2@qa.lab.tlv.redhat.com'
USER3 = 'userportal3@qa.lab.tlv.redhat.com'
USER = USER1

GROUP_USER = 'q-student'
GROUP_NAME = 'Users/q-Students@qa.lab.tlv.redhat.com'

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
TEMPLATE_NAME = 'users__template'
TEMPLATE_NAME2 = 'users__template2'
TEMPLATE_NAME3 = 'users__template3'
TEMPLATE_NAME4 = 'users__template4'
TEMPLATE_NO_DISK = 'users__template_nodisk'
VMPOOL_NAME = 'users__vmpool'
SNAPSHOT_DEF = 'Active VM'
USER_ROLE = 'users__role_user'
ADMIN_ROLE = 'users__role_admin'