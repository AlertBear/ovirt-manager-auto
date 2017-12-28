"""
VMs resume behavior test
"""
import pytest
import config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import tier1, tier2, SlaTest
from helpers import (
    check_vm_status_thread_pool,
)
from rhevmtests.compute.sla.fixtures import (
    update_vms_parametrizied
)
from fixtures import (
    block_unblock_storage,
)
from rhevmtests.fixtures import (  # noqa: F401
    start_vms_fixture_function,
    stop_vms_fixture_function
)


@pytest.mark.usefixtures(
    update_vms_parametrizied.__name__,
    start_vms_fixture_function.__name__,
    block_unblock_storage.__name__
)
class TestResumeBehavior(SlaTest):
    """
    Goal of the tests is to check that three kinds of VMs (non HA, HA no lease,
    HA with lease) behave according to the Resume Behavior settings. For all
    tests the following setup steps (fixtured) are performed:
        1) Start VM with configured Resume Behavior (wait for IP)
        2) Block the Storage
        3) Wait for I/O error
        4) Unblock the Storage, 10 sec after getting I/O error
        5) Check VM status according to Resume Behavior setting.
    The tests check behavior for three VMs from conf.RESUME_BEHAVIOR_VMS ,
    each one with different storage domain: iscsi, nfs, gluster
    """
    start_vms_dict = conf.START_VMS_DICT
    wait_for_vms_ip = True
    vms_to_pause = conf.RESUME_BEHAVIOR_VMS
    time_to_sleep_after_io_error = conf.WAIT_AFTER_IO_ERROR_DEFAULT

    @pytest.mark.parametrize(
        (
            "vm_state_after_io_error",
            "resume_behavior",
            "vms_to_params",
            "sleep_after_io_error"
        ),
        [
            pytest.param(
                *conf.TEST_PARAMS_NON_HA_VM_AUTO_RESUME,
                marks=(polarion("RHEVM-24265"), tier1)
            ),
            pytest.param(
                *conf.TEST_PARAMS_NON_HA_VM_KILL,
                marks=(polarion("RHEVM-24272"), tier1)
            ),
            pytest.param(
                *conf.TEST_PARAMS_NON_HA_LEAVE_PAUSED,
                marks=(polarion("RHEVM-24274"), tier2)
            ),
            pytest.param(
                *conf. TEST_PARAMS_HA_VM_AUTO_RESUME,
                marks=(polarion("RHEVM-24275"), tier2)
            ),
            pytest.param(
                *conf.TEST_PARAMS_HA_VM_KILL,
                marks=(polarion("RHEVM-24270"), tier1)
            ),
            pytest.param(
                *conf.TEST_PARAMS_HA_VM_LEAVE_PAUSED,
                marks=(polarion("RHEVM-24274"), tier2)
            ),
            pytest.param(
                *conf.TEST_PARAMS_HA_VM_WITH_LEASE_KILL,
                marks=(polarion("RHEVM-24270"), tier2)
            )
        ],
        ids=[
            "verify_auto_resume_behavior_for_non_ha_vms",
            "verify_kill_behavior_for_non_ha_vms",
            "verify_leave_paused_behavior_for_non_ha_vms",
            "verify_auto_resume_behavior_for_ha_no_lease_vms",
            "verify_kill_behavior_for_ha_no_lease_vms",
            "verify_leave_paused_behavior_for_ha_no_lease_vms",
            "verify_default_kill_behavior_for_ha_with_lease_vms"
        ]
    )
    def test_vm_status_as_resume_behavior_after_ioerror(
        self,
        vm_state_after_io_error,
        resume_behavior,
        vms_to_params,
        sleep_after_io_error
    ):
        """
        Goal of the test is to check that VM State after block/unblock of
        storage (block storage causes VM I/O error pause) is set according to
        Resume Behavior settings.
        """
        check_vm_status_thread_pool(vm_state_after_io_error, resume_behavior)
