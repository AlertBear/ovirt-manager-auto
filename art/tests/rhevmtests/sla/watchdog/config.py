"""
SLA test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

WATCHDOG_MODEL = PARAMETERS.get('watchdog_model')

GENERAL_VM_PARAMS = {
    'memory': 2 * GB,
    'memory_guaranteed': 2 * GB,
    'os_type': VM_OS_TYPE,
    'placement_affinity': VM_USER_MIGRATABLE,
    'display_type': VM_DISPLAY_TYPE,
    'placement_host': None,  # Filled in setup_package
    'cluster': CLUSTER_NAME[0]
}
INSTALL_VM_PARAMS = {
    'storageDomainName': STORAGE_NAME[0],
    'size': 6 * GB,
    'nic': NIC_NAME[0],
    'network': MGMT_BRIDGE,
    'installation': True,
    'image': COBBLER_PROFILE,
    'user': VMS_LINUX_USER,
    'password': VMS_LINUX_PW
}

WATCHDOG_TIMER = 120  # default time of triggering watchdog * 2
QEMU_CONF = '/etc/libvirt/qemu.conf'
DUMP_PATH = '/var/lib/libvirt/qemu/dump'
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
WATCHDOG_PACKAGE = 'watchdog'
LSHW_PACKAGE = 'lshw'
LSPCI_PACKAGE = 'lspci'
KILLALL_PACKAGE = 'psmisc'
WATCHDOG_CONFIG_FILE = '/etc/watchdog.conf'