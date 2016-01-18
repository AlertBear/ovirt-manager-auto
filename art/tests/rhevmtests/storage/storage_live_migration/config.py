"""
Config module for live storage migration
"""
from rhevmtests.storage.config import *  # flake8: noqa

# Name of the test
TESTNAME = "live_storage_migration"
MIGRATE_SAME_TYPE = None

# TODO: remove this
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']
