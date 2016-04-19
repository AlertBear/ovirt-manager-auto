"""
Config module for storage spm priority
"""
from rhevmtests.storage.config import *  # flake8: noqa

# Priority range
MAX_SPM_PRIORITY = 10
LARGER_THAN_MAX_SPM_PRIORITY = 11
DEFAULT_SPM_PRIORITY = 5
LOW_SPM_PRIORITY = 1
MIN_SPM_PRIORITY = -1
BELOW_MIN_SPM_PRIORITY = -2
ILLEGAL_SPM_PRIORITY = '#'
