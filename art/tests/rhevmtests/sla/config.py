"""
Configuration file for sla tests package
"""

from rhevmtests.config import *  # flake8: noqa

# Power management constants
PM_ADDRESS = "pm_address"
PM_PASSWORD = "pm_password"
PM_USERNAME = "pm_username"
PM_TYPE = "pm_type"
PM_SLOT = "pm_slot"
PM_PORT = "pm_port"

APC_SNMP = "apc_snmp"
APC_SNMP_ADDRESS = "rack04-pdu01-lab4.tlv.redhat.com"
APC_SNMP_USERNAME = "alukiano"
APC_SNMP_PASSWORD = "Al123456"

PMS = {
    "master-vds10.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: "qabc3-mgmt.qa.lab.tlv.redhat.com",
        PM_USERNAME: "USERID",
        PM_PASSWORD: "PASSW0RD",
        PM_TYPE: "bladecenter",
        PM_SLOT: 5
    },
    "cyan-vdsf.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: APC_SNMP_ADDRESS,
        PM_USERNAME: APC_SNMP_USERNAME,
        PM_PASSWORD: APC_SNMP_PASSWORD,
        PM_TYPE: APC_SNMP,
        PM_PORT: 13
    },
    "cyan-vdsg.qa.lab.tlv.redhat.com": {
        PM_ADDRESS: APC_SNMP_ADDRESS,
        PM_USERNAME: APC_SNMP_USERNAME,
        PM_PASSWORD: APC_SNMP_PASSWORD,
        PM_TYPE: APC_SNMP,
        PM_PORT: 12
    }
}

# PPC constants
VM_OS_TYPE = ENUMS["rhel7ppc64"] if PPC_ARCH else ENUMS["rhel6x64"]
VM_DISPLAY_TYPE = ENUMS[
    "display_type_vnc"
] if PPC_ARCH else ENUMS["display_type_spice"]

# VM parameters
VM_MEMORY = "memory"
VM_MEMORY_GUARANTEED = "memory_guaranteed"
VM_MAX_MEMORY = "max_memory"
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
VM_TEMPLATE = "template"
VM_BALLOONING = "ballooning"
VM_QUOTA = "vm_quota"
VM_DISK_QUOTA = "disk_quota"
VM_STORAGE_DOMAIN = "storageDomainName"
VM_DISK_SIZE = "provisioned_size"
VM_NIC = "nic"
VM_NETWORK = "network"
VM_PROTECTED = "protected"
VM_CPU_PROFILE = "cpu_profile_id"

DEFAULT_VM_PARAMETERS = {
    VM_MEMORY: GB,
    VM_MEMORY_GUARANTEED: GB,
    VM_MAX_MEMORY: 4 * GB,
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
    VM_CPU_MODE: "custom",
    VM_PROTECTED: False
}

VM_WITHOUT_DISK = "vm_without_disk_sla"
BLANK_TEMPlATE = "Blank"

DC_QUOTA_MODE = "quota_mode"
QUOTA_NONE_MODE = "NONE"
QUOTA_AUDIT_MODE = "AUDIT"
QUOTA_ENFORCED_MODE = "ENFORCED"
QUOTA_MODES = {
    QUOTA_NONE_MODE: "disabled",
    QUOTA_AUDIT_MODE: "audit",
    QUOTA_ENFORCED_MODE: "enabled"
}
DEFAULT_DC_PARAMETERS = {
    DC_QUOTA_MODE: QUOTA_MODES[QUOTA_NONE_MODE]
}


HOST = "host"
RESOURCE = "resource"

# Cluster overcommitment constants
CLUSTER_OVERCOMMITMENT_NONE = 100
CLUSTER_OVERCOMMITMENT_DESKTOP = 200

# Scheduler policies
POLICY_NONE = "none"
POLICY_POWER_SAVING = ENUMS["scheduling_policy_power_saving"]
POLICY_EVEN_DISTRIBUTION = ENUMS["scheduling_policy_evenly_distributed"]
POLICY_EVEN_VM_DISTRIBUTION = ENUMS["scheduling_policy_vm_evenly_distributed"]
POLICY_IN_CLUSTER_UPGRADE = "InClusterUpgrade"

# Scheduling policies constants
VM_TO_HOST_AFFINITY_UNIT = "VmToHostsAffinityGroups"
VM_TO_VM_AFFINITY_UNIT = "VmAffinityGroups"
AFFINITY_SCHEDULER_FILTERS = [
    "CPUOverloaded",
    VM_TO_VM_AFFINITY_UNIT,
    "CpuPinning",
    "HostDevice",
    "Memory",
    VM_TO_HOST_AFFINITY_UNIT,
    "PinToHost",
    "Network"
]
AFFINITY_SCHEDULER_WEIGHTS = [
    VM_TO_VM_AFFINITY_UNIT,
    VM_TO_HOST_AFFINITY_UNIT,
    "PreferredHosts"
]
AFFINITY_POLICY_NAME = "affinity_policy"

OVER_COMMITMENT_DURATION = "CpuOverCommitDurationMinutes"
HIGH_UTILIZATION = "HighUtilization"
LOW_UTILIZATION = "LowUtilization"
MAX_FREE_MEMORY = "MaxFreeMemoryForOverUtilized"
MIN_FREE_MEMORY = "MinFreeMemoryForUnderUtilized"
HOSTS_IN_RESERVE = "HostsInReserve"

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
DEFAULT_PS_WITH_PM_PARAMS = copy.deepcopy(DEFAULT_PS_PARAMS)
DEFAULT_PS_WITH_PM_PARAMS.update(
    {HOSTS_IN_RESERVE: 1, "EnableAutomaticHostPowerManagement": "true"}
)
DEFAULT_ED_PARAMS = {
    OVER_COMMITMENT_DURATION: OVER_COMMITMENT_DURATION_VALUE,
    HIGH_UTILIZATION: HIGH_UTILIZATION_VALUE
}

LONG_BALANCE_TIMEOUT = 600
SHORT_BALANCE_TIMEOUT = 180
POWER_MANAGEMENT_TIMEOUT = 900

ENGINE_POLICIES = [
    POLICY_NONE,
    POLICY_POWER_SAVING,
    POLICY_EVEN_DISTRIBUTION,
    POLICY_EVEN_VM_DISTRIBUTION,
    POLICY_IN_CLUSTER_UPGRADE
]

BALANCE_LOG_MSG_POSITIVE = (
    "Wait until balance module will migrate VM's on the host %s"
)
BALANCE_LOG_MSG_NEGATIVE = (
    "Check that no migration happens on or from the host %s"
)

ENGINE_CONFIG_LOW_UTILIZATION = "LowUtilizationForEvenlyDistribute"
SERVICE_PUPPET = "puppet"
SERVICE_GUEST_AGENT = "ovirt-guest-agent"

CPU = "cpu"
VCPU = "vcpu"
CPU_AFFINITY = "cpu_affinity"
CPU_MODEL_NAME = "model name"

NUMA_AWARE_KSM_FILE = "/sys/kernel/mm/ksm/merge_across_nodes"

# VM run once constants
VM_RUN_ONCE_HOST = "host"
VM_RUN_ONCE_WAIT_FOR_STATE = "wait_for_state"

UPDATE_SCHEDULER_MEMORY_TIMEOUT = 30
AREM_BALANCE_TIMEOUT = 120

QOS_TYPE_CPU = "cpu"

# Package manager constants
PACKAGE_MANAGER_INSTALL = "install"
PACKAGE_MANAGER_REMOVE = "remove"

# Affinity groups constants
AREM_OPTION = "AffinityRulesEnforcementManagerEnabled"
AFFINITY_GROUP_POSITIVE = "positive"
AFFINITY_GROUP_ENFORCING = "enforcing"
AFFINITY_GROUP_HOSTS = "hosts"
AFFINITY_GROUP_HOSTS_RULES = "hosts_rule"
AFFINITY_GROUP_VMS = "vms"
AFFINITY_GROUP_VMS_RULES = "vms_rule"
AFFINITY_GROUPS_ENABLED = "enabled"

# Cluster constants
CLUSTER_OVERCOMMITMENT = "mem_ovrcmt_prc"
CLUSTER_BALLOONING = "ballooning_enabled"
CLUSTER_KSM = "ksm_enabled"
CLUSTER_SCH_POLICY = "scheduling_policy"
CLUSTER_SCH_POLICY_PROPERTIES = "properties"
CLUSTER_THREADS_AS_CORE = "threads_as_cores"

DEFAULT_CLUSTER_PARAMETERS = {
    CLUSTER_OVERCOMMITMENT: CLUSTER_OVERCOMMITMENT_DESKTOP,
    CLUSTER_BALLOONING: False,
    CLUSTER_KSM: False,
    CLUSTER_SCH_POLICY: POLICY_NONE,
    CLUSTER_THREADS_AS_CORE: False
}

VMS_TO_RUN_0 = vms_to_run = dict(
    (VM_NAME[i], {VM_RUN_ONCE_HOST: i}) for i in xrange(1, 3)
)
VMS_TO_RUN_1 = dict(
    (VM_NAME[i], {VM_RUN_ONCE_HOST: i}) for i in xrange(2)
)
VMS_TO_RUN_2 = dict(
    (VM_NAME[i], {}) for i in xrange(2)
)

ENGINE_STAT_UPDATE_INTERVAL = 15

# I do not have way to recognize what the correct PCI device for the host
# device passthrough test, so I will just add static list with such devices
HOST_DEVICES_TO_ATTACH = [
    "6 Series/C200 Series Chipset Family USB Enhanced Host Controller #2",
    "7500/5520/5500/X58 Trusted Execution Technology Registers"
]
