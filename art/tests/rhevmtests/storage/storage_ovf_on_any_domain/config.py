"""
3.5 Feature: Configuration for OVF on any domain feature
"""
from rhevmtests.storage.config import *  # flake8: noqa

# The 1st two VMs are used by the majority of tests, the 3rd is only used by
# tests that specifically require a new VM created as part of their validations
VM_NAME_1 = "storage_ovf_on_any_domain_1"
VM_NAME_2 = "storage_ovf_on_any_domain_2"
VM_NAME_3 = "storage_ovf_on_any_domain_extra"
TEMPLATE_NAME = "storage_ovf_on_any_domain_template"
POOL_NAME = "storage_ovf_pool_6262"
POOL_SIZE = 5
POOL_DESCRIPTION = "storage_ovf_pool_6262_description"

if STORAGE_TYPE_ISCSI in STORAGE_SELECTOR:
    EXTEND_LUN_ADDRESS = UNUSED_LUN_ADDRESSES
    EXTEND_LUN_TARGET = UNUSED_LUN_TARGETS
    EXTEND_LUN = UNUSED_LUNS
