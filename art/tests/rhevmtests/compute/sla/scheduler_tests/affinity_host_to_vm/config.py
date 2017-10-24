"""
Configuration file for host to VM affinity test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

# HostToVm hard positive group
HOST_TO_VM_AFFINITY_GROUP_1 = {
    AFFINITY_GROUP_HOSTS_RULES: {
        AFFINITY_GROUP_POSITIVE: True,
        AFFINITY_GROUP_ENFORCING: True
    }
}
# HostToVm hard negative group
HOST_TO_VM_AFFINITY_GROUP_2 = {
    AFFINITY_GROUP_HOSTS_RULES: {
        AFFINITY_GROUP_POSITIVE: False,
        AFFINITY_GROUP_ENFORCING: True
    }
}
# HostToVm soft positive group
HOST_TO_VM_AFFINITY_GROUP_3 = {
    AFFINITY_GROUP_HOSTS_RULES: {
        AFFINITY_GROUP_POSITIVE: True,
        AFFINITY_GROUP_ENFORCING: False
    }
}
# HostToVm soft negative group
HOST_TO_VM_AFFINITY_GROUP_4 = {
    AFFINITY_GROUP_HOSTS_RULES: {
        AFFINITY_GROUP_POSITIVE: False,
        AFFINITY_GROUP_ENFORCING: False
    }
}
# Add to affinity groups the VM and the host
for affinity_group in (
    HOST_TO_VM_AFFINITY_GROUP_1,
    HOST_TO_VM_AFFINITY_GROUP_2,
    HOST_TO_VM_AFFINITY_GROUP_3,
    HOST_TO_VM_AFFINITY_GROUP_4
):
    affinity_group[AFFINITY_GROUP_VMS] = VM_NAME[:1]
    affinity_group[AFFINITY_GROUP_HOSTS] = [0]
    affinity_group[AFFINITY_GROUP_VMS_RULES] = {AFFINITY_GROUPS_ENABLED: False}

HOST_TO_VM_AFFINITY_GROUP_5 = {
    AFFINITY_GROUP_HOSTS_RULES: {
        AFFINITY_GROUP_POSITIVE: False,
        AFFINITY_GROUP_ENFORCING: True
    },
    AFFINITY_GROUP_HOSTS: [0, 1],
    AFFINITY_GROUP_VMS: VM_NAME[:1]
}

# VmToVm hard positive affinity group
VM_TO_VM_AFFINITY_GROUP_1 = {
    AFFINITY_GROUP_VMS_RULES: {
        AFFINITY_GROUP_POSITIVE: True,
        AFFINITY_GROUP_ENFORCING: True,
        AFFINITY_GROUPS_ENABLED: True
    },
    AFFINITY_GROUP_VMS: VM_NAME[:2]
}
# VmToVm hard negative affinity group
VM_TO_VM_AFFINITY_GROUP_2 = {
    AFFINITY_GROUP_VMS_RULES: {
        AFFINITY_GROUP_POSITIVE: False,
        AFFINITY_GROUP_ENFORCING: True,
        AFFINITY_GROUPS_ENABLED: True
    },
    AFFINITY_GROUP_VMS: VM_NAME[:3]
}

AFFINITY_START_VM_TEST = "affinity_start_vm"
AFFINITY_MIGRATE_VM_TEST = "affinity_migrate_vm"
AFFINITY_MAINTENANCE_HOST_TEST = "affinity_maintenance_vm"
AFFINITY_ENFORCEMENT_TEST = "affinity_enforcement"
