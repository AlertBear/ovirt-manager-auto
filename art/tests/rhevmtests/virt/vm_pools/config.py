"""
Vm Pool test config
"""
from rhevmtests.networking.config import *  # NOQA

POSITIVE_CREATION_MESSAGE = "Cannot create vm pool: %s"
NEGATIVE_CREATION_MESSAGE = (
    "Vm pool: %s was created with wrong values - check pool's parameters"
)
NEW_IMPLEMENTATION_VERSION = '4.0'
STATELESS_SNAPSHOT_DESCRIPTION = 'stateless snapshot'
PRESTARTED_VMS_TIMEOUT = 300
VM_POOL_ACTION_TIMEOUT = 300
VM_POOL_ACTION_SLEEP = 5
