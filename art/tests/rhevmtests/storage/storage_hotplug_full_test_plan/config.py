"""
Config module for storage hotplug full test plan
"""
from rhevmtests.storage.config import *  # flake8: noqa

CLASS_VM_NAME_FORMAT = "%s_%s_vm"
TESTNAME = 'hotplug_full_test_plan'
VM_NAME = TESTNAME + "_%s_vm"
DISK_NAME_FORMAT = "%s_%s_%s_disk"
TEMPLATE_NAME = "hotplug_full_test_template_%s"
