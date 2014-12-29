""" Test configuration - login data to the servers and test setup options.  """
__test__ = False

from rhevmtests.system.config import *  # flake8:  noqa


def get(lst, index, default):
    try:
        return lst[index]
    except IndexError:
        return default


# Hosts
HOST_ADDRESS = get(HOSTS, 0, None)
HOST_ROOT_PASSWORD = HOSTS_PW
HOST_CPU_TYPE = CPU_NAME

ALT1_HOST_ADDRESS = get(HOSTS, 1, None)
ALT1_HOST_ROOT_PASSWORD = HOSTS_PW
ALT1_HOST_AVAILABLE = True
ALT1_HOST_CPU_TYPE = CPU_NAME

ALT2_HOST_ADDRESS = get(HOSTS, 2, None)
ALT2_HOST_ROOT_PASSWORD = HOSTS_PW
ALT2_HOST_AVAILABLE = True
ALT2_HOST_CPU_TYPE = CPU_NAME

# Networks
NETWORK_NAME = 'rhevm'
NETWORK_NAME1 = 'rhevm1'
NETWORK_NAME2 = 'rhevm2'
NETWORK_NAME3 = 'rhevm3'
NETWORK_NAME4 = 'rhevm4'

# Storages
MAIN_STORAGE_TYPE = PARAMETERS.get('storage_type')
LOCAL = PARAMETERS['local']
NFS_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 0, None)
NFS_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 0, None)

ALT1_STORAGE_NAME = 'users__storage2'
ALT1_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 1, None)
ALT1_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 1, None)
ALT1_STORAGE_AVAILABLE = True

ALT2_STORAGE_NAME = 'users__storage3'
ALT2_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 2, None)
ALT2_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 2, None)
ALT2_STORAGE_AVAILABLE = True

ISO_FILE = 'en_windows_xp_professional_with_service_pack_3_x86_cd_vl_x14-73974.iso'
ISO_ADDRESS = PARAMETERS.as_list('tests_iso_domain_address')[0]
ISO_PATH = PARAMETERS.as_list('tests_iso_domain_path')[0]
EXPORT_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_NAME = 'export_domain_name'
EXPORT_PATH = PARAMETERS.as_list('export_domain_path')[0]

SKIP_ISCSI_TESTS = True
LUN_ADDRESS = '10.34.63.x'
LUN_TARGET = ''
LUN_GUID = ''

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
MAIN_DC_NAME = 'users_dc'
MAIN_CLUSTER_NAME = 'users_cluster'
MAIN_HOST_NAME = 'user_host'
MAIN_STORAGE_NAME = 'user_sd'

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
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

MB = 1024*1024
GB = 1024*MB

#dc_name = users_dc
#cluster_name = users_cl
#host_name = users_host
#storage_name = users_sd
#storage_type = nfs
#alt_cluster_name = user_info_access__cluster
#dc_name_b = user_info_access__dc_b
#cluster_name_b = user_info_access__cluster_b

#def_snap_desc = Active VM

#vm_no_disk = users__vm_nodisk
#template_name = users__template
#template_name2 = users__template2
#template_name3 = users__template3
#template_name4 = users__template4
#template_no_disk = users__template_nodisk
#disk_name = users__disk
#disk_name1 = users__disk1
#vmpool_name = users__vmpool
#role_user_name = users__role_user
#role_admin_name = users__role_admin
#network1 = rhevm
#network2 = rhevm1
#network3 = rhevm2
#network4 = rhevm3
#network5 = rhevm4
#alt1_storage_name = users__storage2
#alt2_storage_name = users__storage3

# Users
#user_domain2 = qa.lab.tlv.redhat.com
#user_name = userportal1
#user_name2 = userportal2
#user_name3 = userportal3
#user1 = userportal1@qa.lab.tlv.redhat.com
#user2 = userportal2@qa.lab.tlv.redhat.com
#user3 = userportal3@qa.lab.tlv.redhat.com

#user_password = 123456
#group_user = q-student
#group_name = qa.lab.tlv.redhat.com/Users/q-Students

# misc
#iso_file = en_windows_xp_professional_with_service_pack_3_x86_cd_vl_x14-73974.iso

#vdc = localhost
#vdc_password = qum5net
