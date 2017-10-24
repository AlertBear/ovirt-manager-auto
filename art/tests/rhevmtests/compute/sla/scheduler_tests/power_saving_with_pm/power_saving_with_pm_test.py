"""
Scheduler - Power Saving with PM Test
Test different cases under power_saving scheduling policy and
with power management enabled on hosts
"""
import copy
import socket
import time

import pytest
import rhevmtests.compute.sla.config as conf
import rhevmtests.compute.sla.helpers as sla_helpers
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    choose_specific_host_as_spm,
    deactivate_hosts,
    migrate_he_vm,
    run_once_vms,
    stop_vms,
    update_cluster,
    update_vms,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helpers
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier3, SlaTest
from fixtures import (
    disable_host_policy_control_flag,
    power_on_host
)
from rhevmtests.compute.sla.scheduler_tests.fixtures import load_hosts_cpu

host_as_spm = 0
he_dst_host = 1


@pytest.fixture(scope="module", autouse=True)
def init_test(request):
    """
    1) Select first host as SPM
    2) Configure power management on hosts
    """
    def fin():
        """
        1) Start the host in case if the host has state DOWN
        2) Remove the power management from the host
        3) Release all hosts from CPU load
        """
        for host_name in conf.HOSTS[:3]:
            host_status_down = (
                ll_hosts.get_host_status(host_name) == conf.HOST_DOWN
            )
            if host_status_down:
                testflow.teardown(
                    "Wait %s seconds between fence operations",
                    conf.FENCE_TIMEOUT
                )
                time.sleep(conf.FENCE_TIMEOUT)
                testflow.teardown("Start the host %s", host_name)
                ll_hosts.fence_host(
                    host=host_name, fence_type="start"
                )
            testflow.teardown(
                "Remove the power management from the host %s", host_name
            )
            hl_hosts.remove_power_management(host_name=host_name)
        testflow.teardown("Free all host CPU's from the load")
        sla_helpers.stop_load_on_resources(
            hosts_and_resources_l=[
                {conf.RESOURCE: conf.VDS_HOSTS[:3], conf.HOST: conf.HOSTS[:3]}
            ]
        )
    request.addfinalizer(fin)

    pm_hosts = dict(zip(conf.HOSTS[:3], conf.VDS_HOSTS[:3]))
    if not sch_helpers.configure_pm_on_hosts(hosts=pm_hosts):
        pytest.skip("Not all hosts have power management")


@pytest.mark.usefixtures(migrate_he_vm.__name__)
class BasePowerSavingWithPM(SlaTest):
    """
    Base class for power saving with power management tests
    """

    @staticmethod
    def _wait_for_hosts_with_state(
        num_of_hosts,
        hosts_state,
        timeout=conf.POWER_MANAGEMENT_TIMEOUT,
        negative=False
    ):
        """
        Wait until given number of hosts will have specific state

        Args:
            num_of_hosts (int): Number of hosts
            hosts_state (str): Hosts expected state
            timeout (int): Sampler timeout
            negative (bool): Positive or negative behaviour

        Returns:
            bool: True, if given number of hosts have expected state
                before timeout reaches, otherwise False
        """
        return sla_helpers.wait_for_hosts_state_in_cluster(
            num_of_hosts=num_of_hosts,
            timeout=timeout,
            sleep=conf.SAMPLER_SLEEP,
            cluster_name=conf.CLUSTER_NAME[0],
            state=hosts_state,
            negative=negative
        )

    def _wait_for_host_shutdown_and_check_host_state(
        self, host_name, host_state
    ):
        """
        1) Wait until the engine will shutdown one of hosts
        2) Check given host state

        Args:
            host_name (str): Host name
            host_state (str): Expected host state
        """
        testflow.step(
            "Wait until one of hosts will have state %s", conf.HOST_DOWN
        )
        assert self._wait_for_hosts_with_state(
            num_of_hosts=1, hosts_state=conf.HOST_DOWN
        )
        testflow.step(
            "Check that the host %s has state %s", host_name, host_state
        )
        assert self._check_host_state(host=host_name, state=host_state)

    @classmethod
    def _check_host_state(cls, host, state):
        """
        Check that host state equals to expected one

        Args:
            host (str): Host name
            state (str): Expected state

        Returns:
            bool: True, if host state equals to expected one
        """
        return ll_hosts.get_host_status(host).lower() == state

    def _wait_for_all_hosts_state_up(self):
        """
        1) Update HostsInReserve scheduling policy parameter to 2
        2) Wait until all hosts will have state UP
        """
        sch_properties = copy.deepcopy(conf.DEFAULT_PS_WITH_PM_PARAMS)
        sch_properties.update({conf.HOSTS_IN_RESERVE: 2})
        assert ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            properties=sch_properties
        )
        testflow.step(
            "Wait until all hosts will have state %s", conf.HOST_UP
        )
        assert self._wait_for_hosts_with_state(
            num_of_hosts=3, hosts_state=conf.HOST_UP
        )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    power_on_host.__name__,
    update_cluster.__name__
)
class PowerSavingWithPMFixtures(BasePowerSavingWithPM):
    """
    Base class for all tests that run with standard fixtures
    """
    vms_to_run = None
    hosts_cpu_load = None
    host_down = None
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_WITH_PM_PARAMS
    }


class TestSPMHostNotKilledByPolicy(PowerSavingWithPMFixtures):
    """
    Test that SPM host does not powered off by the engine
    """
    vms_to_run = conf.VMS_TO_RUN_0
    hosts_cpu_load = {conf.CPU_LOAD_50: [1]}
    host_down = 2

    @tier3
    @polarion("RHEVM3-5572")
    def test_host_with_spm(self):
        """
        Test that SPM host does not powered off by the engine
        """
        self._wait_for_host_shutdown_and_check_host_state(
            host_name=conf.HOSTS[0], host_state=conf.HOST_UP
        )


class TestHostWithoutCPULoadingShutdownByPolicy(PowerSavingWithPMFixtures):
    """
    Test that the engine shutdown the host without CPU load
    """
    vms_to_run = conf.VMS_TO_RUN_0
    hosts_cpu_load = {conf.CPU_LOAD_50: [1]}
    host_down = 2

    @tier3
    @polarion("RHEVM3-5580")
    def test_host_with_cpu_load(self):
        """
        Test that the engine shutdown the host without CPU load
        """
        self._wait_for_host_shutdown_and_check_host_state(
            host_name=conf.HOSTS[1], host_state=conf.HOST_UP
        )


class TestHostStartedByPowerManagement(PowerSavingWithPMFixtures):
    """
    Test that the engine start a host,
    when a user increases the HostsInReserve parameter
    """
    vms_to_run = conf.VMS_TO_RUN_0
    hosts_cpu_load = {conf.CPU_LOAD_50: [1]}
    host_down = 2

    @tier3
    @polarion("RHEVM3-5577")
    def test_start_host(self):
        """
        Test that the engine start a host,
        when a user increases the HostsInReserve parameter
        """
        self._wait_for_host_shutdown_and_check_host_state(
            host_name=conf.HOSTS[2], host_state=conf.HOST_DOWN
        )
        assert helpers.wait_for_host_pm_state(
            pm_command_executor=conf.VDS_HOSTS[1],
            host_resource=conf.VDS_HOSTS[2],
            expected_state=conf.POWER_MANAGEMENT_STATE_OFF
        )
        self._wait_for_all_hosts_state_up()


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    disable_host_policy_control_flag.__name__,
    run_once_vms.__name__,
    power_on_host.__name__,
    update_cluster.__name__
)
class TestCheckPolicyControlOfPowerManagementFlag(BasePowerSavingWithPM):
    """
    Test that the engine does not power off host with
    the disabled 'policy_control_flag'
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0}}
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_WITH_PM_PARAMS
    }
    host_down = 1

    @tier3
    @polarion("RHEVM3-5579")
    def test_disable_policy_control_flag(self):
        """
        Test that the engine does not power off host with
        the disabled 'policy_control_flag'
        """
        testflow.step(
            "Wait until host %s will have state %s",
            conf.HOSTS[2], conf.HOST_DOWN
        )
        assert not ll_hosts.wait_for_hosts_states(
            positive=True,
            names=conf.HOSTS[2],
            states=conf.HOST_DOWN,
            timeout=conf.SHORT_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartHostWhenNoReservedHostLeft(PowerSavingWithPMFixtures):
    """
    Test that the engine start a host, when no hosts left in reserve
    """
    vms_to_run = {conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 1}}
    vms_to_stop = [conf.VM_NAME[1]]

    @tier3
    @polarion("RHEVM3-5576")
    def test_no_reserve_left(self):
        """
        Test that the engine start a host, when no hosts left in reserve
        """
        testflow.step(
            "Wait until one of hosts will have state %s", conf.HOST_DOWN
        )
        assert self._wait_for_hosts_with_state(
            num_of_hosts=1, hosts_state=conf.HOST_DOWN
        )
        assert helpers.wait_for_host_pm_state(
            pm_command_executor=conf.VDS_HOSTS[1],
            host_resource=conf.VDS_HOSTS[2],
            expected_state=conf.POWER_MANAGEMENT_STATE_OFF
        )
        testflow.step(
            "Run once VM %s on the host %s", conf.VM_NAME[1], conf.HOSTS[0]
        )
        assert ll_vms.runVmOnce(
            positive=True, vm=conf.VM_NAME[1], host=conf.HOSTS[0]
        )
        testflow.step(
            "Wait until all hosts will have state %s", conf.HOST_UP
        )
        assert self._wait_for_hosts_with_state(
            num_of_hosts=3, hosts_state=conf.HOST_UP
        )


class TestNoExcessHosts(PowerSavingWithPMFixtures):
    """
    Test that the engine does not shutdown a host,
    when it does not have hosts in reserve
    """
    vms_to_run = dict(
        (conf.VM_NAME[i], {conf.VM_RUN_ONCE_HOST: i}) for i in xrange(3)
    )

    @tier3
    @polarion("RHEVM3-5575")
    def test_reserved_equal_to_up_hosts(self):
        """
        Test that the engine does not shutdown a host,
        when it does not have hosts in reserve
        """
        testflow.step(
            "Check that all hosts stay in state %s", conf.HOST_UP
        )
        assert not self._wait_for_hosts_with_state(
            num_of_hosts=3,
            hosts_state=conf.HOST_UP,
            negative=True,
            timeout=conf.SHORT_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    update_vms.__name__,
    run_once_vms.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__
)
class TestHostStoppedUnexpectedly(BasePowerSavingWithPM):
    """
    Test that the engine power on another host if reserved host died
    """
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_HIGHLY_AVAILABLE: True}
    }
    vms_to_run = conf.VMS_TO_RUN_1
    hosts_cpu_load = {conf.CPU_LOAD_50: [1]}
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_WITH_PM_PARAMS
    }

    @tier3
    @polarion("RHEVM3-5573")
    def test_host_stopped_unexpectedly(self):
        """
        Test that the engine power on another host if reserved host died
        """
        self._wait_for_host_shutdown_and_check_host_state(
            host_name=conf.HOSTS[2], host_state=conf.HOST_DOWN
        )
        assert helpers.wait_for_host_pm_state(
            pm_command_executor=conf.VDS_HOSTS[1],
            host_resource=conf.VDS_HOSTS[2],
            expected_state=conf.POWER_MANAGEMENT_STATE_OFF
        )
        testflow.step("Stop network on the host %s", conf.HOSTS[1])
        try:
            conf.VDS_HOSTS[0].network.if_down(nic=conf.MGMT_BRIDGE)
        except socket.timeout:
            pass

        testflow.step(
            "Wait until the host %s will have %s state",
            conf.HOSTS[0], conf.HOST_NONRESPONSIVE
        )
        assert ll_hosts.wait_for_hosts_states(
            positive=True,
            names=conf.HOSTS[0],
            states=conf.HOST_NONRESPONSIVE
        )

        testflow.step(
            "Wait until some other host in the cluster will have state %s",
            conf.HOST_UP
        )
        assert self._wait_for_hosts_with_state(
            num_of_hosts=2, hosts_state=conf.HOST_UP
        )
        self._wait_for_all_hosts_state_up()


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    run_once_vms.__name__,
    deactivate_hosts.__name__,
    power_on_host.__name__,
    update_cluster.__name__
)
class TestHostStoppedByUser(BasePowerSavingWithPM):
    """
    Test that the engine does not start host that was shutdown by user
    """
    vms_to_run = conf.VMS_TO_RUN_1
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_WITH_PM_PARAMS
    }
    host_down = 2
    hosts_to_maintenance = [2]

    @tier3
    @polarion("RHEVM3-5574")
    def test_host_stopped_by_user(self):
        """
        Test that the engine does not start host that was shutdown by user
        """
        testflow.step(
            "Stop the host %s via power management", conf.HOSTS[2]
        )
        assert ll_hosts.fence_host(host=conf.HOSTS[2], fence_type="stop")
        testflow.step(
            "Check that the host %s stay in state %s",
            conf.HOSTS[2], conf.HOST_DOWN
        )
        assert not self._wait_for_hosts_with_state(
            num_of_hosts=1,
            hosts_state=conf.HOST_DOWN,
            negative=True,
            timeout=conf.SHORT_BALANCE_TIMEOUT
        )
