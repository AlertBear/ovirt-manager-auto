"""
HA reservation test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

GENERAL_VM_PARAMS = {
    'cluster': CLUSTER_NAME[0],
    'memory': GB,
    'placement_host': HOSTS[0],
    'placement_affinity': VM_MIGRATABLE,
    'highly_available': True,
    'os_type': OS_TYPE
}

INSTALL_VM_PARAMS = {
    'storageDomainName': STORAGE_NAME[0],
    'size': DISK_SIZE,
    'nic': NIC_NAME[0],
    'network': MGMT_BRIDGE,
    'installation': False
}

SPECIFIC_VMS_PARAMS = {
    VM_NAME[0]: {
        'highly_available': False,
        'placement_host': HOSTS[0],
        'placement_affinity': VM_PINNED

    },
    VM_NAME[1]: {
        'memory': 4 * GB,
        'memory_guaranteed': 4 * GB,
        'highly_available': True,
        'placement_host': HOSTS[1] if len(HOSTS) >= 2 else None,
        'placement_affinity': VM_MIGRATABLE
    }
}
