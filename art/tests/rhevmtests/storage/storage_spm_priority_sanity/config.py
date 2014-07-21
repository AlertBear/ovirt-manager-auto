"""
Config module for storage SPM priority sanity
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "storage_spm_priority_sanity"

# Hosts settings
# TODO: remove
HOSTS_PWD = HOSTS_PW
VDS_ROOT = HOSTS_USER
VDS_PASSWORDS = HOSTS_PW

# Priority range
MAX_VALUE = PARAMETERS.get('max_value', 10)
MIN_VALUE = PARAMETERS.get('min_value', -1)

# Storage Servers
if STORAGE_TYPE == ENUMS['storage_type_nfs']:
    STORAGE_SERVERS = PARAMETERS.as_list('data_domain_address') + \
        [PARAMETERS['master_export_address']]
    MASTER_VERSION_TAG = 'MASTER_VERSION'
else:
    STORAGE_SERVERS = PARAMETERS.as_list('lun_address') + \
        [PARAMETERS['master_lun_address']]
    MASTER_VERSION_TAG = 'MDT_MASTER_VERSION'

# TODO: remove
DB_HOST = DB_ENGINE_HOST
DB_USER = DB_ENGINE_USER
DB_HOST_PASSWORD = VDC_ROOT_PASSWORD
DB_HOST_USER = VDC_ROOT_USER
