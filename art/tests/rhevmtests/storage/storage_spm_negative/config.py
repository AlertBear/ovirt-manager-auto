"""
Config module for storage spm negative
"""

from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False


# Name of the test
TESTNAME = "storage_spm_negative"

STORAGE_DOMAIN_NAMES = list()

SSL = PARAMETERS.get('ssl', '')

if STORAGE_TYPE == ENUMS['storage_type_nfs']:
    STORAGE_SERVERS = PARAMETERS.as_list('data_domain_address') + \
        [PARAMETERS['master_export_address']]
    MASTER_VERSION_TAG = 'MASTER_VERSION'
else:
    STORAGE_SERVERS = PARAMETERS.as_list('lun_address') + \
        [PARAMETERS['master_lun_address']]
    MASTER_VERSION_TAG = 'MDT_MASTER_VERSION'
