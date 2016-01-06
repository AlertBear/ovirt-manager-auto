"""
Config module for storage Glance sanity
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "glance_sanity"

VM_NAME = "{0}_vm_%s".format(TESTNAME)
DISK_ALIAS = "{0}_disk_%s_%s".format(TESTNAME)
TEMPLATE_NAME = "{0}_template_%s_%s".format(TESTNAME)
