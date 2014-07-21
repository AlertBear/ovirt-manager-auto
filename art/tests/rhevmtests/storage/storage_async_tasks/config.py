"""
Config module for manage storage connections tests
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "async_tasks"

# TODO remove
TEMPLATE_NAME = PARAMETERS.get('template_name', "%s_template" % TESTNAME)

NUMBER_OF_DISKS = int(PARAMETERS.get('no_of_disks', 8))
