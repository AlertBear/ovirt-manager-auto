"""
Config module for clone vm from snapshot
"""

__test__ = False

from rhevmtests.storage.config import *  # flake8: noqa

TESTNAME = "clone_vm_from_snapshot"

SNAPSHOT_NAME = "snapshot_for_clone"

VM_NAME = TESTNAME + "_vm_%s"
VM_DISK_SIZE = 20 * GB
