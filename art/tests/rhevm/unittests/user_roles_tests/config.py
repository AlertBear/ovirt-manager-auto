""" Test configuration - login data to the servers and test setup options.  """

__test__ = False

import os

from . import ART_CONFIG
from utilities.utils import readConfFile

PARAMETERS = 'PARAMETERS'

# server on which ovirt-engine is running.
OVIRT_URL = '%s://%s:%s/api' % ( ART_CONFIG['REST_CONNECTION']['scheme'],
    ART_CONFIG['REST_CONNECTION']['host'], ART_CONFIG['REST_CONNECTION']['port'])
OVIRT_USERNAME = str(ART_CONFIG['REST_CONNECTION']['user'])
OVIRT_DOMAIN = str(ART_CONFIG['REST_CONNECTION']['user_domain'])
OVIRT_PASSWORD = str(ART_CONFIG['REST_CONNECTION']['password'])
OVIRT_VERSION = str(ART_CONFIG[PARAMETERS]['compatibility_version'])

# main host
HOST_ADDRESS =          str(ART_CONFIG[PARAMETERS].as_list('vds')[0])
HOST_ROOT_PASSWORD =    str(ART_CONFIG[PARAMETERS].as_list('vds_password')[0])
HOST_CPU_TYPE =         str(ART_CONFIG[PARAMETERS]['cpu_name'])
HOST_NIC =              str(ART_CONFIG[PARAMETERS].as_list('host_nics')[0])

# alternative host, optional for most tests
# set to True if you want to use it
ALT1_HOST_CPU_TYPE =      str(ART_CONFIG[PARAMETERS]['cpu_name'])
ALT2_HOST_CPU_TYPE =      str(ART_CONFIG[PARAMETERS]['cpu_name'])
try:
    ALT1_HOST_ADDRESS =       str(ART_CONFIG[PARAMETERS].as_list('vds')[1])
    ALT1_HOST_ROOT_PASSWORD = str(ART_CONFIG[PARAMETERS].as_list('vds_password')[1])
    ALT1_HOST_AVAILABLE = True
except IndexError:
    ALT1_HOST_AVAILABLE = False
    ALT1_HOST_ADDRESS = None
    ALT1_HOST_ROOT_PASSWORD = None

try:
    ALT2_HOST_ADDRESS =       str(ART_CONFIG[PARAMETERS].as_list('vds')[2])
    ALT2_HOST_ROOT_PASSWORD = str(ART_CONFIG[PARAMETERS].as_list('vds_password')[2])
    ALT2_HOST_AVAILABLE = True
except IndexError:
    ALT2_HOST_AVAILABLE = False
    ALT2_HOST_ADDRESS = None
    ALT2_HOST_ROOT_PASSWORD = None


# alternative data storage for some tests its needed

# usually 'rhevm' or 'ovirtmgmt'
NETWORK_NAME =          'rhevm'

############################ STORAGE ##########################################
# WARNING - all given storages may be formatted

# either NFS or iSCSI
MAIN_STORAGE_TYPE =     'NFS'

# This will be used as the main storage if MAIN_STORAGE_TYPE == 'NFS'.
# If you don't have any NFS storage, set option SKIP_NFS_TESTS to True
# and use iSCSI only.
# WARNING - the storage will be formatted
NFS_STORAGE_ADDRESS = str(ART_CONFIG[PARAMETERS].as_list('data_domain_address')[0])
NFS_STORAGE_PATH = str(ART_CONFIG[PARAMETERS].as_list('data_domain_path')[0])

try:
    ALT1_STORAGE_NAME    = 'user_api_tests__storage2'
    ALT1_STORAGE_ADDRESS = str(ART_CONFIG[PARAMETERS].as_list('data_domain_address')[1])
    ALT1_STORAGE_PATH    = str(ART_CONFIG[PARAMETERS].as_list('data_domain_path')[1])
    ALT1_STORAGE_AVAILABLE = True
except IndexError:
    ALT1_STORAGE_AVAILABLE = False
    ALT1_STORAGE_NAME    = None
    ALT1_STORAGE_ADDRESS = None
    ALT1_STORAGE_PATH    = None

try:
    ALT2_STORAGE_NAME    = 'user_api_tests__storage3'
    ALT2_STORAGE_ADDRESS = str(ART_CONFIG[PARAMETERS].as_list('data_domain_address')[2])
    ALT2_STORAGE_PATH    = str(ART_CONFIG[PARAMETERS].as_list('data_domain_path')[2])
    ALT2_STORAGE_AVAILABLE = True
except IndexError:
    ALT2_STORAGE_AVAILABLE = False
    ALT2_STORAGE_NAME    = None
    ALT2_STORAGE_ADDRESS = None
    ALT2_STORAGE_PATH    = None


# This will be used as the main storage if MAIN_STORAGE_TYPE == 'iSCSI'
# If you don't have any iSCSI storage, set option SKIP_ISCSI_TESTS to True
# and use NFS only.
SKIP_ISCSI_TESTS =      True
LUN_ADDRESS =           '10.34.63.x'
LUN_TARGET =            ''
LUN_GUID =              ''

# ISO file
ISO_FILE = 'en_windows_xp_professional_with_service_pack_3_x86_cd_vl_x14-73974.iso'

# WARNING - the storage will be formatted
ISO_ADDRESS = str(ART_CONFIG[PARAMETERS].as_list('tests_iso_domain_address')[0])
ISO_PATH = str(ART_CONFIG[PARAMETERS].as_list('tests_iso_domain_path')[0])

# WARNING - the storage will be formatted
EXPORT_ADDRESS = str(ART_CONFIG[PARAMETERS].as_list('export_domain_address')[0])
EXPORT_PATH = str(ART_CONFIG[PARAMETERS].as_list('export_domain_path')[0])

###############################################################################
USER_NAME =             'userportal1'
USER_NAME2 =            'userportal2'
USER_NAME3 =            'userportal3'
USER_DOMAIN =           'qa.lab.tlv.redhat.com'
USER_PASSWORD =         '123456'

GROUP_USER = 'q-student'
GROUP_NAME = 'qa.lab.tlv.redhat.com/Users/q-Students'

############################ OPTIONS ##########################################

# If both SKIP_MAIN_SETUP and SKIP_MAIN_TEARDOWN are False, the script will
# create the main data center, cluster and host at the start of the test and
# remove them at the end.
# If both are set to True, the script will assume that the main data center,
# cluster and host are already created with the names specified here and will
# not remove them at the end.
# See setUpPackage() and tearDownPackage() in __init__.py
SKIP_MAIN_SETUP =       False
SKIP_MAIN_TEARDOWN =    False

# Names of main objects that are created at the start of the test (only once)
# and removed at the end.
MAIN_DC_NAME =          'user_api_tests__dc'
MAIN_CLUSTER_NAME =     'user_api_tests__cluster'
MAIN_HOST_NAME =        'user_api_tests__host'
MAIN_STORAGE_NAME =     'user_api_tests__storage'

# How many seconds to wait for storage or a VM to reach a state before making
# the test fail.
TIMEOUT =               60*2
# How many seconds to wait for the host installation and reboot before making
# the tests fail.
HOST_INSTALL_TIMEOUT =  90*10
