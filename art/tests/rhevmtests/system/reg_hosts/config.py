"""
config module for host regression test
"""
__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

TEST_NAME = "regression_hosts"

DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
