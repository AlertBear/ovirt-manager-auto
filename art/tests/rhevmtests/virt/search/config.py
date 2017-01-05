"""
Search test config
"""
from rhevmtests.virt.config import *  # flake8:  noqa

# VM parameters
VM_CREATED_BY_USER = "vm_created_by_user1"
VM_UP_SEARCH_TEST = "search_vm_test_up_status"
VM_DOWN_SEARCH_TEST = "search_vm_test_down_status"
VMS_SEARCH_TESTS = [VM_UP_SEARCH_TEST, VM_DOWN_SEARCH_TEST, VM_CREATED_BY_USER]
