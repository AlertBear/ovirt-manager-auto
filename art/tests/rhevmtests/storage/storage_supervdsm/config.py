"""
Config module for supervdsm module
"""
from rhevmtests.storage.config import *  # flake8: noqa

SVDSM_LOCK = "/var/run/vdsm/svdsm.sock"
SERVICE_CMD = "/bin/systemctl"

HW_INFO_COMMAND = ["vdsm-client", "Host", "getHardwareInfo"]

SLEEP_SERVICE = 10

# Error messages
ERROR_EXEC_SERVICE_ACTION = "Failed to execute %s on service %s"
ERROR_SERVICE_NOT_UP = "Service %s is not running"
ERROR_SERVICE_UP = "Service %s is running"
ERROR_HW_OUTPUT = "Cannot get HW Info, output:\n%s"
FILE_DOES_NOT_EXIST = "File %s does not exist"
