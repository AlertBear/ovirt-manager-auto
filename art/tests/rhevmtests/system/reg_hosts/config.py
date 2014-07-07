"""
config module for host regression test
"""
__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

TEST_NAME = "regression_hosts"
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TEST_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TEST_NAME)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
