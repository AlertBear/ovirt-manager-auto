"""
Config module for storage disk image format
"""

from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

# Name of the test
TESTNAME = "disk_image_format"

# There's no installation for the moment so make the disk size 1 GB only
DISK_SIZE = GB
