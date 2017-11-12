"""
Configuration File for NUMA test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

CPU_PINNING_TYPE = "Cpus_allowed_list"
MEMORY_PINNING_TYPE = "Mems_allowed_list"

STRICT_MODE = "bind"
PREFER_MODE = "prefer"
INTERLEAVE_MODE = "interleave"

ENGINE_NUMA_MODES = {
    STRICT_MODE: "strict",
    PREFER_MODE: "preferred",
    INTERLEAVE_MODE: "interleave"
}

NUMA_NODE_PARAMS_INDEX = "index"
NUMA_NODE_PARAMS_CORES = "cores"
NUMA_NODE_PARAMS_MEMORY = "memory"
NUMA_NODE_PARAMS_PIN_LIST = "pin_list"

VM_NUMA_PARAMS = {
    NUMA_NODE_CPUS: NUMA_NODE_PARAMS_CORES,
    NUMA_NODE_MEMORY: NUMA_NODE_PARAMS_MEMORY
}

MEMORY_ERROR = 50
CORES_MULTIPLIER = 2

LIBVIRTD_PID_DIRECTORY = "/var/run/libvirt/qemu/"

START_VM_TIMEOUT = 120

DEFAULT_NUMA_NODE_PARAMS = {
    NUMA_NODE_PARAMS_INDEX: 0,
    NUMA_NODE_PARAMS_MEMORY: 1024,
    NUMA_NODE_PARAMS_CORES: [0],
    NUMA_NODE_PARAMS_PIN_LIST: [0]
}
