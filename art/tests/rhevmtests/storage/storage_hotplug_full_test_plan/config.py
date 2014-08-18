"""
Config module for storage hotplug full test plan
"""

__test__ = False

from rhevmtests.storage.config import * # flake8: noqa

DISK_INTERFACES = (ENUMS['interface_virtio'],)

positive = True

# Name of the test
TESTNAME = "hotplug_full_test"
DEFAULT_VM_NAME = "vm_%s" % TESTNAME
VM_NAME_FORMAT = "%s-%sVM"

WAIT_TIME = 120
STORAGE_DOMAIN_NAME = SD_NAMES_LIST[0]

TEMPLATE_NAMES = [TEMPLATE_NAME[0],]  # only use one template
