"""
Virt - VM cpu and machine type
"""
from rhevmtests.compute.virt.reg_vms.config import *  # flake8: noqa

CLUSTER_CPU_NAME = "cluster_name"
CLUSTER_CPU_MODEL = "cluster_cpu_model"
MAX_HOST_CPU = "max_host_cpu"
MIN_HOST_CPU = "min_host_cpu"
HIGER_CPU_MODEL = "higher_cpu_model"
LOWER_CPU_MODEL = "lower_cpu_model"
HIGHEST_COMMON_CPU_MODEL = "highest_common_cpu_model"
CLUSTER_CPU_PARAMS = {
    CLUSTER_CPU_NAME: None,
    CLUSTER_CPU_MODEL: None,
    MAX_HOST_CPU: None,
    MIN_HOST_CPU: None,
    HIGER_CPU_MODEL: None,
    LOWER_CPU_MODEL: None,
    HIGHEST_COMMON_CPU_MODEL: None
}
CLUSTER_UPDATED_CPU = None
NON_EXISTING_TYPE = 'test_non_existing_type'
EMULATED_MACHINE_POLICY_UNIT = 'Emulated-Machine'
CPU_MODEL_POLICY_UNIT = 'CPU-Level'
ADDITIONAL_DISK = 'virt_additional_disk'
