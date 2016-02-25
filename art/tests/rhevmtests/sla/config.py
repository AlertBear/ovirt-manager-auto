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


NUM_OF_DEVICES = int(STORAGE_CONF.get("%s_devices" % STORAGE_TYPE_NFS, 0))
STORAGE_NAME = [
    "_".join([STORAGE_TYPE_NFS, str(i)]) for i in xrange(NUM_OF_DEVICES)
]

# PPC constants
VM_OS_TYPE = ENUMS['rhel7ppc64'] if PPC_ARCH else ENUMS['rhel6x64']
VM_DISPLAY_TYPE = ENUMS[
    'display_type_vnc'
] if PPC_ARCH else ENUMS['display_type_spice']

# VM parameters
VM_MEMORY = "memory"
VM_MEMORY_GUARANTEED = "memory_guaranteed"

DEFAULT_VM_PARAMETERS = {
    VM_MEMORY: GB,
    VM_MEMORY_GUARANTEED: GB,
    'cpu_socket': 1,
    'cpu_cores': 1,
    'os_type': VM_OS_TYPE,
    'type': VM_TYPE_DESKTOP,
    'display_type': VM_DISPLAY_TYPE,
    'placement_affinity': VM_MIGRATABLE,
    'placement_host': VM_ANY_HOST,
    'cluster': CLUSTER_NAME[0],
    'watchdog_model': '',
    'highly_available': False,
    'vcpu_pinning': [],
    'cpu_shares': 0
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
