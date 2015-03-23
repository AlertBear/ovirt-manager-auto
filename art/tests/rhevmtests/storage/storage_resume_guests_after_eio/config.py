"""
Config module for resume guests after storage domain error
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

TESTNAME = "storage_resume_guests_eio"

VM_NAME = TESTNAME

# TODO: remove
VDC_PASSWORD = VDC_ROOT_PASSWORD
