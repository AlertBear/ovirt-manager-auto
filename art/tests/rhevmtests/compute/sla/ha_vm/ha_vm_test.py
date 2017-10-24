"""
HA VM test
Verify the restart of the HA VM under different conditions
"""
import pytest
import rhevmtests.compute.sla.config as conf

import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.helpers as rhevm_helpers
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier1, tier2, tier3, SlaTest
from rhevmtests.compute.sla.fixtures import (
    configure_hosts_power_management,
    migrate_he_vm,
    run_once_vms,
    update_vms,
    wait_for_hosts_status_up
)

he_dst_host = 2


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    update_vms.__name__,
    run_once_vms.__name__
)
class BaseHaVm(SlaTest):
    """
    Base class for all HA VM tests
    """
    vms_to_params = {conf.VM_NAME[0]: {conf.VM_HIGHLY_AVAILABLE: True}}
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        }
    }

    @staticmethod
    def run_action_and_verify_ha_vm_restart(
        method, method_msg, *method_args, **method_kwargs
    ):
        """
        Run the specific method and verify that the engine restarts the HA VM

        Args:
            method (function): Call this method before HA verification
            method_msg (str): Method testflow message
            *method_args (list): Method arguments
            **method_args (dict): Method keyword arguments

        Returns:
            bool: True, if the method succeeds and the events have
                desired message, otherwise False
        """
        last_event_id = ll_events.get_max_event_id()
        testflow.step(method_msg)
        status = method(*method_args, **method_kwargs)
        if status is not None and not status:
            return False
        testflow.step(
            "Verify that the engine restart the HA VM %s", conf.VM_NAME[0]
        )
        sampler = TimeoutingSampler(
            timeout=conf.HA_RESTART_TIMEOUT,
            sleep=conf.SAMPLER_SLEEP,
            func=ll_events.get_all_events_from_specific_event_id,
            code=506,
            start_event_id=last_event_id
        )
        try:
            for sample in sampler:
                if sample:
                    return True
        except APITimeout:
            return False


class TestHaVm01(BaseHaVm):
    """
    Verify that the engine restart the HA VM
    that was unexpectedly killed on the host
    """

    @tier1
    @polarion("RHEVM3-9814")
    def test_restart_of_ha_vm(self):
        """
        1) Kill the HA VM QEMU process on the host
        2) Wait until the engine will restart the HA VM
        """
        method_msg = "Kill the VM %s QEMU process on the host %s" % (
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert self.run_action_and_verify_ha_vm_restart(
            method=ll_hosts.kill_vm_process,
            method_msg=method_msg,
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0]
        )


class TestHaVm02(BaseHaVm):
    """
    Verify that the engine does not restart the HA VM in case when it
    powered off from the engine
    """

    @tier1
    @polarion("RHEVM3-9815")
    def test_restart_of_ha_vm(self):
        """
        Test that the engine does not restart the HA VM
        """
        method_msg = "Power off the HA VM %s from the engine" % conf.VM_NAME[0]
        assert not self.run_action_and_verify_ha_vm_restart(
            method=ll_vms.stopVm,
            method_msg=method_msg,
            positive=True,
            vm=conf.VM_NAME[0]
        )


class TestHaVm03(BaseHaVm):
    """
    Verify that the engine does not restart the HA VM in case when it
    powered off from the guest OS
    """

    @tier1
    @polarion("RHEVM3-9816")
    def test_restart_of_ha_vm(self):
        """
        Test that the engine does not restart the HA VM
        """
        vm_resource = rhevm_helpers.get_vm_resource(
            vm=conf.VM_NAME[0], start_vm=False
        )
        vm_resource.add_power_manager(pm_type="ssh")

        method_msg = "Power off the HA VM %s from the guest OS" % (
            conf.VM_NAME[0]
        )
        assert not self.run_action_and_verify_ha_vm_restart(
            method=vm_resource.get_power_manager().poweroff,
            method_msg=method_msg,
        )


class TestHaVm04(BaseHaVm):
    """
    Verify that the engine does not restart the HA VM in case when it
    suspended from the engine
    """

    @tier2
    @polarion("RHEVM3-9817")
    def test_restart_of_ha_vm(self):
        """
        Test that the engine does not restart the HA VM
        """
        method_msg = "Suspend the HA VM %s from the engine" % conf.VM_NAME[0]
        assert not self.run_action_and_verify_ha_vm_restart(
            method=ll_vms.suspendVm,
            method_msg=method_msg,
            positive=True,
            vm=conf.VM_NAME[0]
        )


@pytest.mark.usefixtures(
    configure_hosts_power_management.__name__,
    wait_for_hosts_status_up.__name__
)
class TestHaVm05(BaseHaVm):
    """
    Verify that the engine restarts the HA VM that ran on the powered off host
    """
    hosts_to_pms = [0]
    hosts_indexes_status_up = [0]

    @tier3
    @polarion("RHEVM3-9821")
    def test_restart_of_ha_vm(self):
        """
        1) Poweroff the host via OS
        2) Test that the engine restarts the HA VM
        """
        conf.VDS_HOSTS[0].add_power_manager(pm_type="ssh")

        method_msg = "Poweroff the host %s" % conf.HOSTS[0]
        assert self.run_action_and_verify_ha_vm_restart(
            conf.VDS_HOSTS[0].get_power_manager().poweroff, method_msg, "-f"
        )


@pytest.mark.usefixtures(
    configure_hosts_power_management.__name__,
    wait_for_hosts_status_up.__name__
)
class TestHaVm06(BaseHaVm):
    """
    Verify that the engine restarts the HA VM that ran
    on the host that restarted via power management
    """
    hosts_to_pms = [0]
    hosts_indexes_status_up = [0]

    @tier3
    @polarion("RHEVM-19634")
    def test_restart_of_ha_vm(self):
        """
        1) Restart the host via power management
        2) Test that the engine restarts the HA VM
        """
        method_msg = "Restart the host %s via power management" % conf.HOSTS[0]
        assert self.run_action_and_verify_ha_vm_restart(
            method=ll_hosts.fence_host,
            method_msg=method_msg,
            host=conf.HOSTS[0],
            fence_type="restart",
            timeout=conf.POWER_MANAGEMENT_TIMEOUT,
            wait_for_status=False
        )
