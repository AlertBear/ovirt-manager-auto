"""
VMs Resume Behavior module
"""
from rhevmtests.compute.sla.config import * # flake8: noqa

# To check 'KILL' resume behavior we need to wait 80 sec after I/O error
# (feature implementation). For other options such sleep is not required
WAIT_AFTER_IO_ERROR_KILL = 80
WAIT_AFTER_IO_ERROR_DEFAULT = 10

ISCSI_VMS = "iscsi"
GLUSTER_VMS = "gluster"
NFS_VMS = "nfs"

# destination host to block
DESTINATION_IP = "address"

RESUME_BEHAVIOR_VMS = []

# For sd_type in [ISCSI_VMS, GLUSTER_VMS, NFS_VMS] when the bz=1481022 is fixed
for sd_type in [ISCSI_VMS]:
    if GE_VMS[sd_type]:
        RESUME_BEHAVIOR_VMS.append(GE_VMS[sd_type][0])

# parameters for start_vms_fixture_function
START_VMS_DICT = dict(
    (vm_name, {}) for vm_name in RESUME_BEHAVIOR_VMS
)

# Test parameters dictionaries include:
# [vm_state_after_io_error - State of VM after storage is unblocked,
# resume_behavior - Resume Behavior Settings,
# vms_to_params - parameters for update_vms_parametrizied fixture
# sleep_after_io_error sleep_after_io_error before unblocking the storage.
# This wait interval for 'KILL' must be not less than 80 sec (engine
# implementation. For other options - leave_paused and auto_resume - it must
# not be 80. The default for tests is 10 sec)

TEST_PARAMS_NON_HA_VM_AUTO_RESUME = [
    VM_UP,
    VM_RB_AUTO_RESUME,
    dict(
        (
            vm, {VM_RESUME_BEHAVIOR: VM_RB_AUTO_RESUME}
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_DEFAULT
]

TEST_PARAMS_NON_HA_VM_KILL = [
    VM_DOWN,
    VM_RB_KILL,
    dict(
        (
            vm, {VM_RESUME_BEHAVIOR: VM_RB_KILL}
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_KILL
]

TEST_PARAMS_NON_HA_LEAVE_PAUSED = [
    VM_PAUSED,
    VM_RB_LEAVE_PAUSED,
    dict(
        (
            vm, {VM_RESUME_BEHAVIOR:VM_RB_LEAVE_PAUSED}
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_DEFAULT
]

TEST_PARAMS_HA_VM_AUTO_RESUME = [
    VM_UP,
    VM_RB_AUTO_RESUME,
    dict(
        (
            vm, {
                VM_RESUME_BEHAVIOR:VM_RB_AUTO_RESUME,
                VM_HIGHLY_AVAILABLE: True,
                VM_LEASE: False
            }
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_DEFAULT
]

TEST_PARAMS_HA_VM_KILL = [
    VM_UP,
    VM_RB_AUTO_RESUME,
    dict(
        (
            vm, {
                VM_RESUME_BEHAVIOR: VM_RB_KILL,
                VM_HIGHLY_AVAILABLE: True,
                VM_LEASE: False
            }
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_KILL
]

TEST_PARAMS_HA_VM_LEAVE_PAUSED = [
    VM_PAUSED,
    VM_RB_LEAVE_PAUSED,
    dict(
        (
            vm, {
                VM_RESUME_BEHAVIOR:VM_RB_LEAVE_PAUSED,
                VM_HIGHLY_AVAILABLE: True,
                VM_LEASE: False
            }
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_DEFAULT
]

TEST_PARAMS_HA_VM_WITH_LEASE_KILL = [
    VM_UP,
    VM_RB_KILL,
    dict(
        (
            vm, {
                VM_RESUME_BEHAVIOR:
                VM_RB_KILL,
                VM_HIGHLY_AVAILABLE: True,
                VM_LEASE: NFS_STORAGE[0]
            }
        )
        for vm in RESUME_BEHAVIOR_VMS
    ),
    WAIT_AFTER_IO_ERROR_DEFAULT
]
