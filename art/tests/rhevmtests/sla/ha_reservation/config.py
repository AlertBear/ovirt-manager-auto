"""
HA reservation test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

HA_RESERVATION_ALLOC = "VM_for_allocation"
HA_RESERVATION_VM = "VM_test_no_RAM"
GENERAL_VM_PARAMS = {
    'cluster': CLUSTER_NAME[0],
    'memory': 7 * GB,
    'placement_host': HOSTS[0],
    'placement_affinity': ENUMS['vm_affinity_migratable'],
    'highly_available': True,
    'os_type': OS_TYPE
}

INSTALL_VM_PARAMS = {
    'storageDomainName': STORAGE_NAME[0],
    'size': DISK_SIZE,
    'nic': NIC_NAME[0],
    'network': MGMT_BRIDGE,
    'installation': True,
    'image': COBBLER_PROFILE,
    'user': VMS_LINUX_USER,
    'password': VMS_LINUX_PW
}

SPECIFIC_VMS_PARAMS = {
    HA_RESERVATION_ALLOC: {
        'highly_available': False,
        'placement_host': HOSTS[0],
        'placement_affinity': ENUMS['vm_affinity_pinned']

    },
    HA_RESERVATION_VM: {
        'highly_available': True,
        'placement_host': HOSTS[1] if len(HOSTS) >= 2 else None,
        'placement_affinity': ENUMS['vm_affinity_migratable']
    }
}
