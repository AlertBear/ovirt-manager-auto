"""
Configuration file for Quota test
"""
from rhevmtests.sla.config import *  # flake8: noqa

DC_NAME_0 = DC_NAME[0]
LIMIT_TYPE_STORAGE = "storage_domain"
LIMIT_TYPE_CLUSTER = "cluster"
VCPU_LIMIT = "vcpu_limit"
MEMORY_LIMIT = "memory_limit"
STORAGE_LIMIT = "limit"
VM_NAME = "quota__vm"
VM_DESC = "quota"
TMP_VM_NAME = "quota__tpm_vm"
DISK_NAME = "quota_disk"
TEMPLATE_NAME = "quota__template"
TMP_TEMPLATE_NAME = "quota__template_tmp"
VM_SNAPSHOT = "quota_vm__snapshot"
QUOTA_NAME = "quota_1"
QUOTA_DESC = "quota_1_desc"
QUOTA2_NAME = "quota_2"
QUOTA2_DESC = "quota_2_desc"
QUOTA_NONE_MODE = "NONE"
QUOTA_AUDIT_MODE = "AUDIT"
QUOTA_ENFORCED_MODE = "ENFORCED"
QUOTA_MODES = {
    QUOTA_NONE_MODE: "disabled",
    QUOTA_AUDIT_MODE: "audit",
    QUOTA_ENFORCED_MODE: "enabled"
}
NONE_TYPE = "NONE"
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
EVENT_TIMEOUT = 10
MEMORY_USAGE = "memory_usage"
VCPU_USAGE = "vcpu_usage"
STORAGE_USAGE = "usage"
SIZE_2_GB = 2 * GB
SIZE_1228_MB = 1228 * MB
