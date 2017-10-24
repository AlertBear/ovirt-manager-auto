"""
HA reservation test config module
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

GENERAL_VM_PARAMS = {
    VM_CLUSTER: CLUSTER_NAME[0],
    VM_PLACEMENT_AFFINITY: VM_MIGRATABLE,
    VM_PLACEMENT_HOSTS: [0],
    VM_HIGHLY_AVAILABLE: True,
    VM_OS: VM_OS_TYPE,
    VM_DISPLAY: VM_DISPLAY_TYPE
}

MULTI_VMS_PARAMS = dict(GENERAL_VM_PARAMS)
MULTI_VMS_PARAMS.update(
    {
        VM_MEMORY: GB / 2,
        VM_MEMORY_GUARANTEED: GB / 2,
        'storageDomainName': STORAGE_NAME[0],
        'provisioned_size': DISK_SIZE,
        'nic': NIC_NAME[0],
        'network': MGMT_BRIDGE,
        'installation': False
    }
)

SPECIFIC_VMS_PARAMS = {
    VM_NAME[0]: {
        VM_HIGHLY_AVAILABLE: False,
        VM_PLACEMENT_AFFINITY: VM_PINNED

    },
    VM_NAME[1]: {
        VM_HIGHLY_AVAILABLE: True,
        VM_PLACEMENT_AFFINITY: VM_MIGRATABLE
    }
}

TMP_LOG = '/tmp/HA_reservation.log'
RESERVATION_TIMEOUT = 70
HA_RESERVATION_INTERVAL = "VdsHaReservationIntervalInMinutes"
NEW_RESERVATION_INTERVAL = 1
DEFAULT_RESERVATION_INTERVAL = 5
