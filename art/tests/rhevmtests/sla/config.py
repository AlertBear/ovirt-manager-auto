"""
Configuration file for sla tests package
"""

from rhevmtests.config import *  # flake8: noqa

# Power management constants
PM_ADDRESS = 'pm_address'
PM_PASSWORD = 'pm_password'
PM_USERNAME = 'pm_username'
PM_TYPE = 'pm_type'
PM_SLOT = 'pm_slot'


# PPC constants
VM_OS_TYPE = ENUMS['rhel7ppc64'] if PPC_ARCH else ENUMS['rhel6x64']
VM_DISPLAY_TYPE = ENUMS[
    'display_type_vnc'
] if PPC_ARCH else ENUMS['display_type_spice']

# VM parameters
VM_MEMORY = "memory"
VM_MEMORY_GUARANTEED = "memory_guaranteed"
VM_PLACEMENT_AFFINITY = "placement_affinity"
VM_PLACEMENT_HOST = "placement_host"
VM_PLACEMENT_HOSTS = "placement_hosts"
VM_HIGHLY_AVAILABLE = "highly_available"
VM_CPU_PINNING = "vcpu_pinning"
VM_CPU_SOCKET = "cpu_socket"
VM_CPU_CORES = "cpu_cores"
VM_CPU_MODE = "cpu_mode"
VM_OS = "os_type"
VM_TYPE = "type"
VM_DISPLAY = "display_type"
VM_CLUSTER = "cluster"
VM_WATCHDOG_MODEL = "watchdog_model"
VM_CPU_SHARES = "cpu_shares"

DEFAULT_VM_PARAMETERS = {
    VM_MEMORY: GB,
    VM_MEMORY_GUARANTEED: GB,
    VM_CPU_SOCKET: 1,
    VM_CPU_CORES: 1,
    VM_OS: VM_OS_TYPE,
    VM_TYPE: VM_TYPE_DESKTOP,
    VM_DISPLAY: VM_DISPLAY_TYPE,
    VM_PLACEMENT_AFFINITY: VM_MIGRATABLE,
    VM_PLACEMENT_HOST: VM_ANY_HOST,
    VM_CLUSTER: CLUSTER_NAME[0],
    VM_WATCHDOG_MODEL: "",
    VM_HIGHLY_AVAILABLE: False,
    VM_CPU_PINNING: [],
    VM_CPU_SHARES: 0,
    VM_CPU_MODE: "none"
}

HOST = "host"
RESOURCE = "resource"

# Cluster overcommitment constants
CLUSTER_OVERCOMMITMENT_NONE = 100
CLUSTER_OVERCOMMITMENT_DESKTOP = 200

# Scheduler policies
POLICY_NONE = "none"
POLICY_POWER_SAVING = ENUMS['scheduling_policy_power_saving']
POLICY_EVEN_DISTRIBUTION = ENUMS['scheduling_policy_evenly_distributed']
POLICY_EVEN_VM_DISTRIBUTION = ENUMS['scheduling_policy_vm_evenly_distributed']

# Scheduling policies constants
OVER_COMMITMENT_DURATION = "CpuOverCommitDurationMinutes"
HIGH_UTILIZATION = "HighUtilization"
LOW_UTILIZATION = "LowUtilization"
MAX_FREE_MEMORY = "MaxFreeMemoryForOverUtilized"
MIN_FREE_MEMORY = "MinFreeMemoryForUnderUtilized"

CPU_LOAD_0 = 0
CPU_LOAD_25 = 25
CPU_LOAD_50 = 50
CPU_LOAD_100 = 100

HIGH_UTILIZATION_VALUE = 75
LOW_UTILIZATION_VALUE = 35
OVER_COMMITMENT_DURATION_VALUE = 1

CLUSTER_POLICY_NAME = "name"
CLUSTER_POLICY_PARAMS = "params"

DEFAULT_PS_PARAMS = {
    OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION_VALUE,
    HIGH_UTILIZATION: HIGH_UTILIZATION_VALUE,
    LOW_UTILIZATION: LOW_UTILIZATION_VALUE,
}
DEFAULT_ED_PARAMS = {
    OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION_VALUE,
    HIGH_UTILIZATION: HIGH_UTILIZATION_VALUE
}

LONG_BALANCE_TIMEOUT = 600
SHORT_BALANCE_TIMEOUT = 180

ENGINE_POLICIES = [
    POLICY_NONE,
    POLICY_POWER_SAVING,
    POLICY_EVEN_DISTRIBUTION,
    POLICY_EVEN_VM_DISTRIBUTION
]

BALANCE_LOG_MSG_POSITIVE = (
    "Wait until balance module will migrate VM's on host %s"
)
BALANCE_LOG_MSG_NEGATIVE = "Check that no migration happen on or from host %s"

ENGINE_CONFIG_LOW_UTILIZATION = "LowUtilizationForEvenlyDistribute"
SERVICE_PUPPET = "puppet"
SERVICE_GUEST_AGENT = "ovirt-guest-agent"

CPU = "cpu"
VCPU = "vcpu"
CPU_AFFINITY = "cpu_affinity"
CPU_MODEL_NAME = "model name"
