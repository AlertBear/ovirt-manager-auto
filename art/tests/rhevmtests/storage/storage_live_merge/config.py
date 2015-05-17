"""
Config module for storage live merge
"""
__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "live_merge"

VM_NAME = TESTNAME + "_vm_%s"
DISK_SIZE = 1 * GB
