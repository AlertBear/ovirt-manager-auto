"""
Configuration file for scheduler_policies_with_memory package
"""
from rhevmtests.sla.config import *  # flake8: noqa

# Memory constants
MEMORY = "memory"
MEMORY_GUARANTEED = "memory_guaranteed"

# Load VMS
LOAD_NORMALUTILIZED_VMS = ["vm_normalutilized_%d" % i for i in range(2)]
LOAD_OVERUTILIZED_VMS = ["vm_overutilized_%d" % i for i in range(2)]
LOAD_MEMORY_VMS = {}

# CPU load constants
CPU_LOAD_0 = 0
CPU_LOAD_50 = 50
CPU_LOAD_100 = 100

# Scheduler policy constants
CLUSTER_POLICY_NAME = "name"
CLUSTER_POLICY_PARAMS = "params"
CLUSTER_POLICY_NONE = "none"
CLUSTER_POLICY_PS = ENUMS['scheduling_policy_power_saving']
OVER_COMMITMENT_DURATION = "CpuOverCommitDurationMinutes"
HIGH_UTILIZATION = "HighUtilization"
LOW_UTILIZATION = "LowUtilization"
MAX_FREE_MEMORY = "MaxFreeMemoryForOverUtilized"
MIN_FREE_MEMORY = "MinFreeMemoryForUnderUtilized"
DEFAULT_PS_PARAMS = {
    OVER_COMMITMENT_DURATION: 1,
    HIGH_UTILIZATION: 75,
    LOW_UTILIZATION: 35,
}

MIGRATION_TIMEOUT = 180
