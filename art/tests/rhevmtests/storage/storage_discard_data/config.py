"""
Config module for storage_domain discard data
"""
from rhevmtests.storage.config import *  # flake8: noqa

DD_SIZE = 0.5 * GB
DATA_CENTER_NAME = DC_NAME[0]
DISK_SIZE = 5 * GB
INITIAL_LUN_USED_SIZE = None
USED_SIZE_BEFORE_DELETE = None
DISK_ALLOCATIONS = {False: 'preallocated', True: 'thin'}

DELETE_DISK = 'delete_disk'
COLD_MOVE = 'cold_move'
LIVE_STORAGE_MIGRATION = 'live_storage_migration'
LIVE_MERGE = 'live_merge'
COLD_MERGE = 'cold_merge'
COLD_MERGE_WITH_MEMORY = 'cold_merge_with_memory'
PREVIEW_UNDO_SNAPSHOT = 'preview_undo_snapshot'
RESTORE_SNAPSHOT = 'restore_snapshot'
RESTORE_SNAPSHOT_WITH_MEMORY = 'restore_snapshot_with_memory'
REMOVE_SNAPSHOT_SINGLE_DISK = 'remove_snapshot_single_disk'

SNAPSHOT_FLOWS = [
    LIVE_MERGE, COLD_MERGE, COLD_MERGE_WITH_MEMORY, PREVIEW_UNDO_SNAPSHOT,
    PREVIEW_UNDO_SNAPSHOT, RESTORE_SNAPSHOT, RESTORE_SNAPSHOT_WITH_MEMORY,
    REMOVE_SNAPSHOT_SINGLE_DISK
]
