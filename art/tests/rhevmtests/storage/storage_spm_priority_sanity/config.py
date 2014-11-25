"""
Config module for storage SPM priority sanity
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

# Name of the test
TESTNAME = "storage_spm_priority_sanity"

# Priority range
MAX_VALUE = PARAMETERS.get('max_value', 10)
MIN_VALUE = PARAMETERS.get('min_value', -1)

NUMBER_OF_HOSTS = 3
TEST_HOSTS = []
TEST_HOSTS_PRIORITIES = {}

spms_136167 = [4,4,6]
spms_136169 = [-1,-1,-1]
spms_136171 = [1,2,3]
spms_136468 = [-1,-1,2]
spms_136466 = [5,5,5]
spms_136168 = [5,5,-1]
spms_136447 = [-1,-1,10]
