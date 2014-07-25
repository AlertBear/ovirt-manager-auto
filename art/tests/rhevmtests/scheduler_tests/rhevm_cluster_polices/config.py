"""
Rhevm Cluster Policies Test configuration module
"""

from rhevmtests.config import *  # flake8: noqa

VM_FOR_MIGRATION = config.VM_NAME[0]
SUPPORT_VM_1 = config.VM_NAME[1]
SUPPORT_VM_2 = config.VM_NAME[2]
LOAD_HOST_0 = config.HOSTS[0]
LOAD_HOST_1 = config.HOSTS[1]
LOAD_HOST_2 = config.HOSTS[2]
VMS = [SUPPORT_VM_1, SUPPORT_VM_2]
