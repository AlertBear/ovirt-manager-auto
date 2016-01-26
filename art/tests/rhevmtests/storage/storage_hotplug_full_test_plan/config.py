"""
Config module for storage hotplug full test plan
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

DISK_INTERFACES = (ENUMS['interface_virtio'],)

TESTNAME = "hotplug_full_test"

CLASS_VM_NAME_FORMAT = "%s_%s_vm"
VM_NAME = TESTNAME + "_%s_vm"

DISK_NAME_FORMAT = "%s_%s_%s_disk"

WAIT_TIME = 120

TEMPLATE_NAME = TESTNAME + "_template_%s"
