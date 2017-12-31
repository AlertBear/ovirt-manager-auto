"""
Configuration file for high performance VM test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

HIGH_PERFORMANCE_POOL = "high_performance_pool"
HIGH_PERFORMANCE_TEMPLATE = "high_performance_template"
HIGH_PERFORMANCE_VM = "high_performance_vm"

# Threads
THREAD_QEMU = "qemu-kvm"
THREAD_IO = "IO"

# CPU and NUMA pinning values
NUMA_NODE_0 = None
NUMA_NODE_1 = None
