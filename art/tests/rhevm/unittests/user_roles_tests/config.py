""" Test configuration - login data to the servers and test setup options.  """
__test__ = False


class FakeObject():
    def get(self, arg):
        pass

    def as_list(self, arg):
        return self

    def __getitem__(self, key):
        pass

try:
    from . import ART_CONFIG
except ImportError:
    ART_CONFIG = {'PARAMETERS': FakeObject(), 'REST_CONNECTION': FakeObject()}


def get(lst, index, default):
    try:
        return lst[index]
    except IndexError:
        return default


PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
OVIRT_URL = '%s://%s:%s/api' % (REST_CONNECTION.get('scheme'),
                                REST_CONNECTION.get('host'),
                                REST_CONNECTION.get('port'))
OVIRT_USERNAME = str(REST_CONNECTION.get('user'))
OVIRT_DOMAIN = str(REST_CONNECTION.get('user_domain'))
OVIRT_PASSWORD = str(REST_CONNECTION.get('password'))
OVIRT_VERSION = PARAMETERS.get('compatibility_version')

OVIRT_IP = PARAMETERS.get('vdc')
OVIRT_PSW = PARAMETERS.get('vdc_password')

# Hosts
HOST_ADDRESS = get(PARAMETERS.as_list('vds'), 0, None)
HOST_ROOT_PASSWORD = get(PARAMETERS.as_list('vds_password'), 0, None)
HOST_CPU_TYPE = PARAMETERS.get('cpu_name')
HOST_NIC = get(PARAMETERS.as_list('host_nics'), 0, None)

ALT1_HOST_ADDRESS = get(PARAMETERS.as_list('vds'), 1, None)
ALT1_HOST_ROOT_PASSWORD = get(PARAMETERS.as_list('vds_password'), 1, None)
ALT1_HOST_AVAILABLE = True
ALT1_HOST_CPU_TYPE = PARAMETERS.get('cpu_name')

ALT2_HOST_ADDRESS = get(PARAMETERS.as_list('vds'), 2, None)
ALT2_HOST_ROOT_PASSWORD = get(PARAMETERS.as_list('vds_password'), 2, None)
ALT2_HOST_AVAILABLE = True
ALT2_HOST_CPU_TYPE = PARAMETERS.get('cpu_name')

# Networks
NETWORK_NAME = PARAMETERS.get('network1')
NETWORK_NAME1 = PARAMETERS.get('network2')
NETWORK_NAME2 = PARAMETERS.get('network3')
NETWORK_NAME3 = PARAMETERS.get('network4')
NETWORK_NAME4 = PARAMETERS.get('network5')

# Storages
MAIN_STORAGE_TYPE = PARAMETERS.get('storage_type')
LOCAL = PARAMETERS['local']
NFS_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 0, None)
NFS_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 0, None)

ALT1_STORAGE_NAME = PARAMETERS.get('alt1_storage_name')
ALT1_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 1, None)
ALT1_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 1, None)
ALT1_STORAGE_AVAILABLE = True

ALT2_STORAGE_NAME = PARAMETERS.get('alt2_storage_name')
ALT2_STORAGE_ADDRESS = get(PARAMETERS.as_list('data_domain_address'), 2, None)
ALT2_STORAGE_PATH = get(PARAMETERS.as_list('data_domain_path'), 2, None)
ALT2_STORAGE_AVAILABLE = True

ISO_FILE = PARAMETERS.get('iso_file')
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
USER_NAME = PARAMETERS.get('user_name')
USER_NAME2 = PARAMETERS.get('user_name2')
USER_NAME3 = PARAMETERS.get('user_name3')
USER_DOMAIN = PARAMETERS.get('user_domain2')
USER_PASSWORD = PARAMETERS.get('user_password')

USER1 = PARAMETERS.get('user1')
USER2 = PARAMETERS.get('user2')
USER3 = PARAMETERS.get('user3')
USER = USER1

GROUP_USER = PARAMETERS.get('group_user')
GROUP_NAME = PARAMETERS.get('group_name')

# Misc
MAIN_DC_NAME = PARAMETERS.get('dc_name')
MAIN_CLUSTER_NAME = PARAMETERS.get('cluster_name')
MAIN_HOST_NAME = PARAMETERS.get('host_name')
MAIN_STORAGE_NAME = PARAMETERS.get('storage_name')

ALT_CLUSTER_NAME = PARAMETERS.get('alt_cluster_name')
DC_NAME_B = PARAMETERS.get('dc_name_b')
CLUSTER_NAME_B = PARAMETERS.get('cluster_name_b')

TIMEOUT = 60*2
HOST_INSTALL_TIMEOUT = 90*10

# Objects
DISK_NAME = PARAMETERS.get('disk_name')
DISK_NAME1 = PARAMETERS.get('disk_name1')
VM_NAME = PARAMETERS.get('vm_name')
VM_NAME1 = PARAMETERS.get('vm_name1')
VM_NAME2 = PARAMETERS.get('vm_name2')
VM_NAME3 = PARAMETERS.get('vm_name3')
VM_NAME4 = PARAMETERS.get('vm_name4')
VM_NO_DISK = PARAMETERS.get('vm_no_disk')
TEMPLATE_NAME = PARAMETERS.get('template_name')
TEMPLATE_NAME2 = PARAMETERS.get('template_name2')
TEMPLATE_NAME3 = PARAMETERS.get('template_name3')
TEMPLATE_NAME4 = PARAMETERS.get('template_name4')
TEMPLATE_NO_DISK = PARAMETERS.get('template_no_disk')
VMPOOL_NAME = PARAMETERS.get('vmpool_name')
SNAPSHOT_DEF = PARAMETERS.get('def_snap_desc')
USER_ROLE = PARAMETERS.get('role_user_name')
ADMIN_ROLE = PARAMETERS.get('role_admin_name')
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']

MB = 1024*1024
GB = 1024*MB
