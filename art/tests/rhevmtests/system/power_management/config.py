"""
power management config module
"""
from art.test_handler.settings import opts

from rhevmtests.system.config import *  # flake8: noqa

ENUMS = opts['elements_conf']['RHEVM Enums']
VM_TYPE = ENUMS['vm_type_server']
FORMAT = ENUMS['format_raw']
FENCE_RESTART = ENUMS['fence_type_restart']
FENCE_START = ENUMS['fence_type_start']
FENCE_STOP = ENUMS['fence_type_stop']
FENCE_STATUS = ENUMS['fence_type_status']

FENCING_TIMEOUT = 500

TEST_NAME = "power_management"
