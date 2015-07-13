from rhevmtests.storage.config import *  # flake8: noqa

__test__ = False

TESTNAME = PARAMETERS.get('basename', 'auto_activate_disk')

VM_START = 'start'
VM_STOP = 'stop'
VM_SUSPEND = 'suspend'
