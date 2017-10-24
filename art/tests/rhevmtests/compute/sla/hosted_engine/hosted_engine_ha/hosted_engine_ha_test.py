"""
Hosted Engine - HA Test
Check behaviour of ovirt-ha-agent under different conditions
"""
import re

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier3, SlaTest
from fixtures import (
    block_connection_to_storage,
    change_he_gateway_address,
    enable_global_maintenance_on_host,
    enable_local_maintenance_on_host,
    get_host_with_he_vm,
    init_he_ha_test,
    load_host_cpu_to_maximum,
    prepare_env_for_next_test,
    prepare_env_for_power_management_test,
    restart_host_via_power_management,
    stop_network_on_host_with_he_vm,
    stop_services
)


@pytest.mark.usefixtures(
    init_he_ha_test.__name__,
    get_host_with_he_vm.__name__,
    prepare_env_for_next_test.__name__
)
class HostedEngineTest(SlaTest):
    """
    Base class that include basic functions for whole test
    """
    he_vm_host = None
    hosts_without_he_vm = None
    command_executor = None

    def he_vm_restarted(self, hosts_resources):
        """
        1) Check that one of hosts run HE VM
        2) Check that engine has a good state

        Args:
            hosts_resources (list): Host resources
        """
        hosts_ips = [host_resource.ip for host_resource in hosts_resources]
        testflow.step(
            "Check if the HE VM starts on the host from the list: %s",
            hosts_ips
        )
        assert helpers.wait_for_hosts_he_vm_up_state(
            command_executor=self.command_executor,
            hosts_resources=hosts_resources,
        )

        testflow.step(
            "Check if the engine runs on the host from the list: %s",
            hosts_ips
        )
        assert helpers.wait_for_hosts_he_vm_health_state(
            command_executor=self.command_executor,
            hosts_resources=hosts_resources,
            timeout=conf.WAIT_FOR_STATE_TIMEOUT
        )

    def stop_service_and_check_he_vm(self, service_name):
        """
        1) Stop the service on the HE VM
        2) Check that HE VM restarted on some host

        Args:
            service_name (str): Service name
        """
        testflow.step(
            "%s: stop the %s service", conf.ENGINE_HOST, service_name
        )
        assert conf.ENGINE_HOST.service(service_name).stop()

        testflow.step("Check that the engine has a bad state")
        assert helpers.wait_for_host_he_vm_health_bad(
            command_executor=self.command_executor,
            host_resource=self.he_vm_host
        )

        host_resources = list(self.hosts_without_he_vm)
        host_resources.append(self.he_vm_host)
        self.he_vm_restarted(hosts_resources=host_resources)


@pytest.mark.usefixtures(
    restart_host_via_power_management.__name__,
    stop_network_on_host_with_he_vm.__name__,
)
class TestHostWithHeVmLostConnection(HostedEngineTest):
    """
    Stop network on the host where HE VM runs and check that
    HE VM starts on a another host
    """

    @tier3
    @polarion("RHEVM3-5536")
    def test_he_vm_restart(self):
        """
        Check if HE VM started on the another host
        """
        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


@pytest.mark.usefixtures(block_connection_to_storage.__name__)
class TestBlockAccessToStorageDomainFromHost(HostedEngineTest):
    """
    Block the access to the HE storage domain via iptables and check that
    HE VM starts on a another host
    """

    @tier3
    @polarion("RHEVM3-5514")
    def test_he_vm_restart(self):
        """
        Check if HE VM started on the another host
        """
        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


class TestShutdownHeVm(HostedEngineTest):
    """
    Shutdown the HE VM and check that
    HE VM starts on a another host
    """

    @tier3
    @polarion("RHEVM3-5528")
    def test_he_vm_restart(self):
        """
        1) Shutdown the HE VM
        2) Check if HE VM started on some host
        """
        cmd = ["shutdown", "-h", "now"]
        testflow.step("Shutdown HE VM from the guest OS")
        helpers.get_output_from_run_cmd(
            host_resource=conf.ENGINE_HOST, cmd=cmd, negative=True
        )

        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


class TestStopEngineService(HostedEngineTest):
    """
    Stop the ovirt-engine service on the HE VM and check that
    HE VM starts on some host
    """

    @tier3
    @polarion("RHEVM3-5533")
    def test_he_vm_restart(self):
        """
        1) Stop ovirt-engine on the HE VM
        2) Check if HE VM started on some host
        """
        self.stop_service_and_check_he_vm(service_name=conf.OVIRT_SERVICE)


class TestStopPostgresqlService(HostedEngineTest):
    """
    Stop the postgresql service on the HE VM and check that
    HE VM starts on some host
    """

    @tier3
    @polarion("RHEVM3-5520")
    def test_he_vm_restart(self):
        """
        1) Stop postgresql service on the HE VM
        2) Check if HE VM started on some host
        """
        self.stop_service_and_check_he_vm(service_name=conf.POSTGRESQL_SERVICE)


class TestKernelPanicOnEngineVm(HostedEngineTest):
    """
    Simulate kernel panic on the HE VM and check that
    HE VM starts on some host
    """

    @tier3
    @polarion("RHEVM3-5527")
    def test_check_hosted_engine_vm(self):
        """
        1) Initiate kernel panic on the HE VM OS
        2) Check that HE VM restarted on some host
        """
        cmd = ["echo", "c", ">", "/proc/sysrq-trigger"]
        helpers.get_output_from_run_cmd(
            host_resource=conf.ENGINE_HOST, cmd=cmd, negative=True
        )
        testflow.step("Check that the engine has a bad state")
        assert helpers.wait_for_host_he_vm_health_bad(
            command_executor=self.command_executor,
            host_resource=self.he_vm_host
        )

        host_resources = list(self.hosts_without_he_vm)
        host_resources.append(self.he_vm_host)
        self.he_vm_restarted(hosts_resources=host_resources)


class TestSanlockStatusOnHosts(HostedEngineTest):
    """
    Check sanlock status for hosts HE hosts
    """

    @tier3
    @polarion("RHEVM3-5531")
    def test_check_sanlock_status_on_host_with_he_vm(self):
        """
        Check sanlock status for the host with the HE VM
        """
        testflow.step(
            "%s: check that the sanlock status equals to 'share'",
            self.he_vm_host
        )
        assert helpers.host_has_sanlock_share(host_resource=self.he_vm_host)

    @tier3
    @polarion("RHEVM3-5532")
    def test_check_sanlock_status_on_host_without_he_vm(self):
        """
        Check sanlock status for the host without the HE VM
        """
        testflow.step(
            "%s: check that the sanlock status equals to 'free'",
            self.hosts_without_he_vm[0]
        )
        assert not helpers.host_has_sanlock_share(
            host_resource=self.hosts_without_he_vm[0]
        )


class TestStartTwoEngineVmsOnHost(HostedEngineTest):
    """
    Start the HE VM on the same or on different host, when it already runs
    """
    command = [conf.HOSTED_ENGINE_CMD, "--vm-start"]

    @tier3
    @polarion("RHEVM3-5524")
    def test_start_two_he_vms_on_the_same_host(self):
        """
        Negative: Try to start two HE VM's on the same host
        and check the return message
        """
        correct_message = "VM exists and its status is Up"
        testflow.step("%s: start the HE VM", self.he_vm_host)
        out = helpers.get_output_from_run_cmd(
            host_resource=self.he_vm_host, cmd=self.command, negative=True
        )
        assert out.strip('\n') == correct_message

    @tier3
    @polarion("RHEVM3-5513")
    def test_start_he_vm_on_second_host_when_it_already_run_on_first(self):
        """
        Negative: Try to start HE VM on the second host, when it already
        runs on the first host and check the return message
        """
        host_without_he_vm = self.hosts_without_he_vm[0]
        testflow.step("%s: start the HE VM", host_without_he_vm)
        helpers.get_output_from_run_cmd(
            host_resource=host_without_he_vm, cmd=self.command
        )

        testflow.step(
            "%s: check via vdsClient that HE VM does not exist",
            host_without_he_vm
        )
        assert not helpers.wait_for_he_vm_via_vdsm(
            host_resource=host_without_he_vm
        )


class TestSynchronizeStateBetweenHosts(HostedEngineTest):
    """
    Check that both hosts have the same output of the HE status command
    """

    @tier3
    @polarion("RHEVM3-5534")
    def test_check_he_status_on_hosts(self):
        """
        Check if HE status equals on both hosts
        """
        statuses = []
        host_resources = list(self.hosts_without_he_vm)
        host_resources.append(self.he_vm_host)
        cmd = [conf.HOSTED_ENGINE_CMD, "--vm-status"]
        for host_resource in host_resources:
            out = re.sub(
                r'\n.*timestamp.*|'
                r'\n.*crc32.*|'
                r'\n.*refresh_time.*|'
                r'\n.*timeout.*',
                '',
                host_resource.run_command(command=cmd)[1]
            )
            statuses.append(out)
        testflow.step(
            "Check that all hosts have the same output "
            "of the HE status command"
        )
        assert all(status == statuses[0] for status in statuses[1:])


@pytest.mark.usefixtures(change_he_gateway_address.__name__)
class TestHostGatewayProblem(HostedEngineTest):
    """
    Change gateway address on the host where runs HE VM
    and check that HE VM starts on a another host with the better score
    """

    @tier3
    @polarion("RHEVM3-5535")
    def test_he_vm_and_host_score(self):
        """
        Check the host score and the HE VM migration
        """
        testflow.step(
            "%s: wait for the HE score %s",
            self.he_vm_host, conf.GATEWAY_SCORE
        )
        assert helpers.wait_for_host_he_score(
            command_executor=self.command_executor,
            host_resource=self.he_vm_host,
            expected_score=conf.GATEWAY_SCORE
        )

        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


@pytest.mark.usefixtures(load_host_cpu_to_maximum.__name__)
class TestHostCpuLoadProblem(HostedEngineTest):
    """
    Load the CPU on the host where runs the HE VM and check the score and
    HE VM migration
    """

    @tier3
    @polarion("RHEVM3-5525")
    def test_host_score_and_he_vm_migration(self):
        """
        Check that host score dropped to 2400 and
        that vm migrated to second host as a result of difference in scores
        """
        testflow.step(
            "%s: wait for the HE score %s",
            self.he_vm_host, conf.CPU_LOAD_SCORE
        )
        assert helpers.wait_for_host_he_score(
            command_executor=self.command_executor,
            host_resource=self.he_vm_host,
            expected_score=conf.CPU_LOAD_SCORE,
            timeout=conf.CPU_SCORE_TIMEOUT
        )

        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


@pytest.mark.usefixtures(enable_global_maintenance_on_host.__name__)
class TestGlobalMaintenance(HostedEngineTest):
    """
    Enable global maintenance on the host and kill the HE VM
    """

    @tier3
    @polarion("RHEVM3-5516")
    def test_kill_vm_and_check_that_nothing_happen(self):
        """
        Kill the HE vm and check that he-agent doesn't try to restart the HE VM
        """
        cmd = [conf.HOSTED_ENGINE_CMD, "--vm-poweroff"]
        testflow.step("%s: kill the HE VM ", self.he_vm_host)
        assert self.he_vm_host.run_command(command=cmd)

        testflow.step(
            "Check that the ha-agent does not restart the HE VM"
        )
        assert not helpers.wait_for_hosts_he_vm_health_state(
            command_executor=self.command_executor,
            hosts_resources=self.hosts_without_he_vm,
        )


@pytest.mark.usefixtures(enable_local_maintenance_on_host.__name__)
class TestLocalMaintenance(HostedEngineTest):
    """
    Put the host with the HE VM to the local maintenance and check the
    host score and HE VM migration
    """

    @tier3
    @polarion("RHEVM3-5517")
    def test_host_score_and_he_vm_migration(self):
        """
        Check that the host under the local maintenance has score zero and
        check that HE VM migrated on the host with the better score
        """
        testflow.step(
            "%s: wait for the HE score %s",
            self.he_vm_host, conf.ZERO_SCORE
        )
        assert helpers.wait_for_host_he_score(
            command_executor=self.command_executor,
            host_resource=self.he_vm_host,
            expected_score=conf.ZERO_SCORE,
        )

        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)


@pytest.mark.usefixtures(stop_services.__name__)
class StopServices(HostedEngineTest):
    """
    Stop HE services and check the HE VM behaviour
    """
    services_to_stop = None
    services_to_start = None


class TestStopBrokerService(StopServices):
    """
    Stop the ovirt-ha-broker service on the host with HE VM,
    and check that the HE VM does not migrate on a another host
    """
    services_to_stop = [conf.BROKER_SERVICE]
    services_to_start = [conf.BROKER_SERVICE, conf.AGENT_SERVICE]

    @tier3
    @polarion("RHEVM3-5521")
    def test_that_he_vm_runs_on_old_host(self):
        """
        Check that the HE VM stays on the old host
        """
        testflow.step(
            "Check that the HE VM runs on the host %s", self.he_vm_host
        )
        assert helpers.wait_for_he_vm_via_vdsm(
            host_resource=self.he_vm_host,
            expected_state=conf.VM_VDSM_STATE_UP
        )


class TestStopAgentService(StopServices):
    """
    Stop ovirt-ha-agent service on host with HE vm,
    and check that vm not migrate to second host
    """
    services_to_stop = [conf.AGENT_SERVICE]
    services_to_start = [conf.AGENT_SERVICE]

    @tier3
    @polarion("RHEVM3-5523")
    def test_that_he_vm_runs_on_old_host(self):
        """
        Check that the HE VM stays on the old host
        """
        testflow.step(
            "Check that the HE VM runs on the host %s", self.he_vm_host
        )
        assert helpers.wait_for_he_vm_via_vdsm(
            host_resource=self.he_vm_host,
            expected_state=conf.VM_VDSM_STATE_UP
        )


class TestStopAgentAndBrokerServices(StopServices):
    """
    Stop ovirt-ha-broker and ovirt-ha-agent service on host with HE vm,
    and check that vm not migrate to second host
    """
    services_to_stop = [conf.AGENT_SERVICE, conf.BROKER_SERVICE]
    services_to_start = [conf.AGENT_SERVICE, conf.BROKER_SERVICE]

    @tier3
    @polarion("RHEVM3-5522")
    def test_that_he_vm_runs_on_old_host(self):
        """
        Check that the HE VM stays on the old host
        """
        testflow.step(
            "Check that the HE VM runs on the host %s", self.he_vm_host
        )
        assert helpers.wait_for_he_vm_via_vdsm(
            host_resource=self.he_vm_host,
            expected_state=conf.VM_VDSM_STATE_UP
        )


@pytest.mark.usefixtures(
    restart_host_via_power_management.__name__,
    prepare_env_for_power_management_test.__name__
)
class TestFenceFlowWhenHostWithHeVmKilled(HostedEngineTest):
    """
    Kill the host with the HE VM and check that the engine continue the
    fence flow after restart of the HE VM
    """

    @tier3
    @polarion("RHEVM-19148")
    def test_fence_flow(self):
        """
        1) Check that HE VM started on the other host
        2) Check that HA VM started on the other host
        3) Check that problematic host fenced by the engine
        """
        self.he_vm_restarted(hosts_resources=self.hosts_without_he_vm)

        testflow.step("Wait for the VM %s state 'UP'", conf.VM_NAME[0])
        assert ll_vms.waitForVMState(vm=conf.VM_NAME[0])

        host_name = conf.HOSTS[conf.VDS_HOSTS.index(self.he_vm_host)]
        testflow.step("Wait for the host %s state 'UP'", host_name)
        assert ll_hosts.wait_for_hosts_states(positive=True, names=host_name)
