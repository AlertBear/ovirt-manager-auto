"""
Config module for resume guests after storage domain error
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "storage_resume_guests_eio"

# TODO: what is this used for?
PARAMETERS['data_domain_address'] = PARAMETERS['static_domain_address']
PARAMETERS['data_domain_path'] = PARAMETERS['static_domain_path']

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD
if STORAGE_TYPE == STORAGE_TYPE_NFS:
    STORAGE_SERVER = PARAMETERS.as_list('static_domain_address')[0]
elif STORAGE_TYPE == STORAGE_TYPE_ISCSI:
    STORAGE_SERVER = LUN_ADDRESS[0]
