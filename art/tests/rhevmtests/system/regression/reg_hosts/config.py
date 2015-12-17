"""
config module for host regression test
"""
__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

TEST_NAME = "regression_hosts"

DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
PM1_ADDRESS = '10.35.35.35'
PM2_ADDRESS = '10.11.11.11'
PM_TYPE_DEFAULT = 'apc'
PM1_USER = 'user1'
PM2_USER = 'user2'
PM1_PASS = 'pass1'
PM2_PASS = 'pass2'
