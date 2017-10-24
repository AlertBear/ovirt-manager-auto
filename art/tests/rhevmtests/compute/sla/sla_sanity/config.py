"""
Configuration file for sla sanity test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

PROTECTED_VM_NAME = "protected_vm"
DEFAULT_VCPU_PINNING = [{"0": "0"}]
