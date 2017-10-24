"""
Search test config
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa

# VM parameters
VM_CREATED_BY_USER = "vm_created_by_user1"
VM_UP_SEARCH_TEST = "search_vm_test_up_status"
VM_DOWN_SEARCH_TEST = "search_vm_test_down_status"
VMS_SEARCH_TESTS = [VM_UP_SEARCH_TEST, VM_DOWN_SEARCH_TEST, VM_CREATED_BY_USER]

SHOW_USER_CMD = "ovirt-aaa-jdbc-tool user show %s" % USER
ADD_USER_CMD = (
    "ovirt-aaa-jdbc-tool user add %s --attribute=firstName=%s"
    " --attribute=department=Quality Assurance" % (USER, USER)
)
RESET_USER_PASSWORD_CMD = (
    "ovirt-aaa-jdbc-tool user password-reset %s --password=pass:%s "
    "--password-valid-to='2050-01-01 00:00:00Z' " % (USER, VDC_PASSWORD)
)
