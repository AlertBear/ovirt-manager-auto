"""
Config module for storage bug coverage test set
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# TODO remove
if PARAMETERS.get('vds_admin', None) is not None:
    ADMINS = PARAMETERS.as_list('vds_admin')
else:
    ADMINS = ['root'] * len(PASSWORDS)

# TODO remove
DOMAIN_NAME_1 = SD_NAME_0
