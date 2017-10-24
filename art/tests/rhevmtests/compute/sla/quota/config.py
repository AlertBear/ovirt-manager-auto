"""
Configuration file for Quota test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

# Limit constants
LIMIT_TYPE_STORAGE = "storage_domain"
LIMIT_TYPE_CLUSTER = "cluster"
VCPU_LIMIT = "vcpu_limit"
MEMORY_LIMIT = "memory_limit"
STORAGE_LIMIT = "limit"
DEFAULT_CPU_LIMIT = 2
MINIMAL_CPU_LIMIT = 1
DEFAULT_MEMORY_LIMIT = 1

VM_NAME = "quota__vm"
TMP_VM_NAME = "quota__tpm_vm"
DISK_NAME = "quota_disk"
TEMPLATE_NAME = "quota__template"
VM_SNAPSHOT = "quota_vm__snapshot"
QUOTA_NAME = "quota_1"
QUOTA_DESC = "quota_1_desc"
QUOTA2_NAME = "quota_2"
QUOTA2_DESC = "quota_2_desc"
GRACE_TYPE = "GRACE"
EXCEED_TYPE = "EXCEED"
GRACE_MSG = "limit exceeded and entered the grace zone"
EXCEED_AUDIT = "limit exceeded, proceeding since in Permissive (Audit) mode"
EXCEED_ENFORCED = "limit exceeded and operation was blocked"
QUOTA_EVENTS = {
    QUOTA_AUDIT_MODE: {
        GRACE_TYPE: GRACE_MSG,
        EXCEED_TYPE: EXCEED_AUDIT
    },
    QUOTA_ENFORCED_MODE: {
        GRACE_TYPE: GRACE_MSG,
        EXCEED_TYPE: EXCEED_ENFORCED
    }
}
NUM_OF_CPUS = {
    GRACE_TYPE: 2,
    EXCEED_TYPE: 3
}
MEMORY_USAGE = "memory_usage"
VCPU_USAGE = "vcpu_usage"
STORAGE_USAGE = "usage"
VM_MEMORY = "memory"
VM_CPU_CORES = "cpu_cores"

# Sizes constants
SIZE_512_MB = 512 * MB
SIZE_1280_MB = 1280 * MB
SIZE_2_GB = 2 * GB
SIZE_10_GB = 10 * GB
SIZE_14_GB = 14 * GB
SIZE_15_GB = 15 * GB

# BZ constants
VERSION_35 = "3.5"
BZ_ENGINE = "engine"
BZ_VERSION = "version"

# Usage constants
DEFAULT_MEMORY_USAGE = 0.5
DEFAULT_CPU_USAGE = 1.0
DEFAULT_DISK_USAGE = 10.0
FULL_DISK_USAGE = 20.0
ZERO_USAGE = 0.0
DEFAULT_USAGES = {
    VCPU_USAGE: DEFAULT_CPU_USAGE,
    MEMORY_USAGE: DEFAULT_MEMORY_USAGE
}
ZERO_USAGES = {
    VCPU_USAGE: ZERO_USAGE,
    MEMORY_USAGE: ZERO_USAGE
}

QUOTA_CLUSTER_LIMIT = "quota_cluster_limit"
QUOTA_STORAGE_LIMIT = "quota_storage_limit"
