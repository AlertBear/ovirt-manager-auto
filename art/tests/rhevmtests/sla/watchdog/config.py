"""
SLA test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

WATCHDOG_MODEL = PARAMETERS.get('watchdog_model')

GENERAL_VM_PARAMS = {
    'memory': 2 * GB,
    'memory_guaranteed': 2 * GB,
    'os_type': OS_TYPE,
    'placement_affinity': ENUMS['vm_affinity_user_migratable'],
    'placement_host': HOSTS[0],
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

