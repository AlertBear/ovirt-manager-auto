""" Test configuration - login data to the servers and test setup options. """

__test__ = False


from art.test_handler.settings import ART_CONFIG
from art.test_handler.settings import opts

PARAMETERS = ART_CONFIG['PARAMETERS']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']
ENUMS = opts['elements_conf']['RHEVM Enums']

TEST_NAME = 'quota_tests'
# server on which ovirt-engine is running.
OVIRT_ADDRESS = PARAMETERS['host']
OVIRT_ROOT = 'root'
OVIRT_ROOT_PASSWORD = PARAMETERS['vdc_password']
OVIRT_VERSION = PARAMETERS['compatibility_version']

DB_NAME = {'RHEVM_DB_NAME': RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
           'OVIRT_DB_NAME': RHEVM_UTILS_ENUMS['OVIRT_DB_NAME']}

# main host
HOST_ADDRESS = PARAMETERS.as_list('vds')[0]
HOST_ROOT_PASSWORD = PARAMETERS.as_list('vds_password')[0]
HOST_CPU_TYPE = PARAMETERS['cpu_name']
HOST_NIC = PARAMETERS.as_list('host_nics')[0]

# alternative host, optional for most tests
# set to True if you want to use it
ALT1_HOST_CPU_TYPE = PARAMETERS['cpu_name']
ALT2_HOST_CPU_TYPE = PARAMETERS['cpu_name']
try:
    ALT1_HOST_ADDRESS = PARAMETERS.as_list('vds')[1]
    ALT1_HOST_ROOT_PASSWORD = PARAMETERS.as_list('vds_password')[1]
    ALT1_HOST_AVAILABLE = True
except IndexError:
    ALT1_HOST_AVAILABLE = False
    ALT1_HOST_ADDRESS = None
    ALT1_HOST_ROOT_PASSWORD = None

# alternative data storage for some tests its needed

# usually 'rhevm' or 'ovirtmgmt'
NETWORK_NAME = 'rhevm'

############################ STORAGE #########################################
# WARNING - all given storages may be formatted

# either NFS or iSCSI
MAIN_STORAGE_TYPE = 'nfs'

# This will be used as the main storage if MAIN_STORAGE_TYPE == 'NFS'.
# If you don't have any NFS storage, set option SKIP_NFS_TESTS to True
# and use iSCSI only.
# WARNING - the storage will be formatted
NFS_STORAGE_ADDRESS = PARAMETERS.as_list('data_domain_address')[0]
NFS_STORAGE_PATH = PARAMETERS.as_list('data_domain_path')[0]

try:
    ALT1_STORAGE_NAME = '%s_%d' % (MAIN_STORAGE_TYPE, 1)
    ALT1_STORAGE_ADDRESS = PARAMETERS.as_list('data_domain_address')[1]
    ALT1_STORAGE_PATH = PARAMETERS.as_list('data_domain_path')[1]
    ALT1_STORAGE_AVAILABLE = True
except IndexError:
    ALT1_STORAGE_AVAILABLE = False
    ALT1_STORAGE_NAME = None
    ALT1_STORAGE_ADDRESS = None
    ALT1_STORAGE_PATH = None

# WARNING - the storage will be formatted
EXPORT_ADDRESS = PARAMETERS.as_list('export_domain_address')[0]
EXPORT_PATH = PARAMETERS.as_list('export_domain_path')[0]

##############################################################################
USER_NAME = PARAMETERS.get('user_name1')
USER_NAME2 = PARAMETERS.get('user_name2')
USER_NAME3 = PARAMETERS.get('user_name3')
USER_DOMAIN = PARAMETERS.get('users_domain')
USER_PASSWORD = PARAMETERS.get('user_password')

GROUP_USER = PARAMETERS.get('group_user')
GROUP_NAME = PARAMETERS.get('group_name')

############################ OPTIONS #########################################

# If both SKIP_MAIN_SETUP and SKIP_MAIN_TEARDOWN are False, the script will
# create the main data center, cluster and host at the start of the test and
# remove them at the end.
# If both are set to True, the script will assume that the main data center,
# cluster and host are already created with the names specified here and will
# not remove them at the end.
# See setup_package() and teardown_package() in __init__.py
SKIP_MAIN_SETUP = PARAMETERS.get('skip_main_setup', False)
SKIP_MAIN_TEARDOWN = PARAMETERS.get('skip_main_teardown', False)

# Names of main objects that are created at the start of the test (only once)
# and removed at the end.
MAIN_DC_NAME = PARAMETERS.get('dc_name')
MAIN_CLUSTER_NAME = PARAMETERS.get('cluster_name')
MAIN_HOST_NAME = HOST_ADDRESS
MAIN_STORAGE_NAME = '%s_%d' % (MAIN_STORAGE_TYPE, 0)

# How many seconds to wait for storage or a VM to reach a state before making
# the test fail.
TIMEOUT = 60*2
# How many seconds to wait for the host installation and reboot before making
# the tests fail.
HOST_INSTALL_TIMEOUT = 90*10

cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')
NIC = 'nic1'

# Parameters for disk creation
DISK_FORMAT = ENUMS['format_cow']
DISK_INTERFACE = ENUMS['interface_virtio']
