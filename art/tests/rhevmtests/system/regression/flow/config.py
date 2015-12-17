"""
Config module for user and roles tests
"""

from rhevmtests.config import *  # flake8: noqa

# NOTE: Adding domain after userame because of AAA
USER_DOMAIN = '%s-authz' % AD_USER_DOMAIN
USER_VDCADMIN_NAME = AD_USERNAME
USER_VDCADMIN = '%s@%s' % (AD_USERNAME, AD_USER_DOMAIN)
USERNAME_NAME = 'rhevmtest'
USERNAME = '%s@%s' % (USERNAME_NAME, AD_USER_DOMAIN)
USER_NON_EXISTING = 'user_doesnt_exist'

GROUP = "Everyone"
