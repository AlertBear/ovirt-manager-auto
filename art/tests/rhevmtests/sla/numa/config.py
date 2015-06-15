"""
Configuration File for NUMA test
"""
from rhevmtests.sla.config import *  # flake8: noqa

NUMACTL_PACKAGE = "numactl"

NUMACTL = "numactl"
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

NUMA_NODE = "node"
NUMA_NODE_DISTANCE = "distances"
NUMA_NODE_MEMORY = "size"
NUMA_NODE_CPUS = "cpus"

VM_NUMA_PARAMS = {
    NUMA_NODE_CPUS: "cores",
    NUMA_NODE_MEMORY: "memory"
}

MEMORY_ERROR = 50
CORES_MULTIPLIER = 2

TCMS_PLAN_ID = "14300"
LIBVIRTD_PID_DIRECTORY = "/var/run/libvirt/qemu/"

START_VM_TIMEOUT = 120
