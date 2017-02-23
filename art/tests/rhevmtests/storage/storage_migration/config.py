"""
Config module for live storage migration
"""
from rhevmtests.storage.config import *  # flake8: noqa

MIGRATE_SAME_TYPE = None
DISK_NAMES = dict()
LIVE_MOVE = True

HOST_STATE_TIMEOUT = 3600
REBOOT_CMD = 'reboot'
