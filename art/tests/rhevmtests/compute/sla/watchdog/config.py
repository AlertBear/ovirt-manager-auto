"""
SLA test config module
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

WATCHDOG_MODEL = 'i6300esb'

WATCHDOG_TIMER = 70
QEMU_CONF = "/etc/libvirt/qemu.conf"
DUMP_PATH = "/var/lib/libvirt/qemu/dump"
ENGINE_LOG = "/var/log/ovirt-engine/engine.log"
ENGINE_TEMP_LOG = "/tmp/watchdog_test_event.log"
WATCHDOG_PACKAGE = "watchdog"
LSHW_PACKAGE = "lshw"
LSPCI_PACKAGE = "lspci"
WATCHDOG_CONFIG_FILE = "/etc/watchdog.conf"

# Watchdog actions
WATCHDOG_ACTION_NONE = "none"
WATCHDOG_ACTION_RESET = "reset"
WATCHDOG_ACTION_POWEROFF = "poweroff"
WATCHDOG_ACTION_PAUSE = "pause"
WATCHDOG_ACTION_DUMP = "dump"

# Template test constants
VM_FROM_TEMPLATE_WATCHDOG = "vm_from_template_watchdog"
WAIT_FOR_VM_STATUS_SLEEP = 2
