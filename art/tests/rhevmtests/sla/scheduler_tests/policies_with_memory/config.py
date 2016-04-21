"""
Configuration file for scheduler_policies_with_memory package
"""
from rhevmtests.sla.config import *  # flake8: noqa

# Load VMS
LOAD_NORMALUTILIZED_VMS = ["vm_normalutilized_%d" % i for i in range(2)]
LOAD_OVERUTILIZED_VMS = ["vm_overutilized_%d" % i for i in range(2)]
LOAD_MEMORY_VMS = {}

