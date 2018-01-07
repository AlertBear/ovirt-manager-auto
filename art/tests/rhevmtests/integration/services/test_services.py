"""
Sanity testing of services on hosts
"""
import pytest

from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier1,
)
from art.unittest_lib import testflow
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.rhevm_api import resources

from services_base import ServicesTest
import config

hosts_rhel = []
hosts_rhvh = []


@pytest.fixture(scope="module", autouse=True)
def setup_package():
    host_objs = ll_hosts.get_host_list()
    if not host_objs:
        raise EnvironmentError("This environment doesn't include hosts")

    for host in host_objs:
        host_type = host.get_type()

        resource_host = resources.Host(host.address)
        resource_host.users.append(
            resources.RootUser(config.VDC_ROOT_PASSWORD)
        )

        if host_type == config.HOST_RHEL:
            hosts_rhel.append(resource_host)
        elif host_type == config.HOST_RHVH:
            hosts_rhvh.append(resource_host)
        else:
            raise EnvironmentError("Unknown host type {} - {} [{}]".format(
                host_type, host.name, host.address
            ))
        testflow.setup(
            "Found %s host - %s [%s]",
            host_type, host.name, host.address
        )


class TestServicesSanity(ServicesTest):
    """Sanity testclass for services"""

    arguments_dict = {
        "test_{0}_{1}_{2}".format(machine, service, action):
            (machine, service, action)
        for machine in config.MACHINES
        for service in config.SERVICES
        for action in config.ACTIONS
        if service in config.MACHINE_SERVICES[machine]
    }

    # initiate empty bz map
    bz_map = {
        i: {}
        for i in arguments_dict.keys()
    }

    # add bugzilla ids
    for tc in (
        "test_{0}_{1}_{2}".format(machine, service, action)
        for machine in config.MACHINES
        for service in config.BUGGED_SERVICES
        for action in config.ACTIONS
        if service in config.MACHINE_SERVICES[machine]
    ):
        for s in config.BUGGED_SERVICES:
            if s in tc:
                bz_map[tc] = {config.BUGGED_SERVICES[s]: {}}

    polarion_map = {
        # engine tests ids
        'test_engine_ovirt-engine_running': 'RHEVM-19472',
        'test_engine_ovirt-engine_enabled': 'RHEVM-19473',
        'test_engine_ovirt-engine_is-faultless': 'RHEVM-19738',
        'test_engine_ovirt-engine-dwhd_running': 'RHEVM-19474',
        'test_engine_ovirt-engine-dwhd_enabled': 'RHEVM-19475',
        'test_engine_ovirt-engine-dwhd_is-faultless': 'RHEVM-19739',
        'test_engine_ovirt-fence-kdump-listener_running': 'RHEVM-19480',
        'test_engine_ovirt-fence-kdump-listener_enabled': 'RHEVM-19481',
        'test_engine_ovirt-fence-kdump-listener_is-faultless': 'RHEVM-19742',
        'test_engine_ovirt-imageio-proxy_running': 'RHEVM-19476',
        'test_engine_ovirt-imageio-proxy_enabled': 'RHEVM-19477',
        'test_engine_ovirt-imageio-proxy_is-faultless': 'RHEVM-19740',
        'test_engine_ovirt-vmconsole-proxy-sshd_running': 'RHEVM-19478',
        'test_engine_ovirt-vmconsole-proxy-sshd_enabled': 'RHEVM-19479',
        'test_engine_ovirt-vmconsole-proxy-sshd_is-faultless': 'RHEVM-19741',
        'test_engine_ovirt-websocket-proxy_running': 'RHEVM-19482',
        'test_engine_ovirt-websocket-proxy_enabled': 'RHEVM-19483',
        'test_engine_ovirt-websocket-proxy_is-faultless': 'RHEVM-19743',
        # rhel tests ids
        'test_host_rhel_vdsmd_running': 'RHEVM-19488',
        'test_host_rhel_vdsmd_enabled': 'RHEVM-19489',
        'test_host_rhel_vdsmd_is-faultless': 'RHEVM-19746',
        'test_host_rhel_supervdsmd_running': 'RHEVM-19492',
        'test_host_rhel_supervdsmd_enabled': 'RHEVM-19493',
        'test_host_rhel_supervdsmd_is-faultless': 'RHEVM-19748',
        'test_host_rhel_sanlock_running': 'RHEVM-19496',
        'test_host_rhel_sanlock_enabled': 'RHEVM-19497',
        'test_host_rhel_sanlock_is-faultless': 'RHEVM-19750',
        'test_host_rhel_libvirtd_running': 'RHEVM-19500',
        'test_host_rhel_libvirtd_enabled': 'RHEVM-19501',
        'test_host_rhel_libvirtd_is-faultless': 'RHEVM-19752',
        'test_host_rhel_mom-vdsm_running': 'RHEVM-19504',
        'test_host_rhel_mom-vdsm_enabled': 'RHEVM-19505',
        'test_host_rhel_mom-vdsm_is-faultless': 'RHEVM-19754',
        'test_host_rhel_ovirt-imageio-daemon_running': 'RHEVM-19508',
        'test_host_rhel_ovirt-imageio-daemon_enabled': 'RHEVM-19509',
        'test_host_rhel_ovirt-imageio-daemon_is-faultless': 'RHEVM-19756',
        'test_host_rhel_ovirt-vmconsole-host-sshd_running': 'RHEVM-19512',
        'test_host_rhel_ovirt-vmconsole-host-sshd_enabled': 'RHEVM-19513',
        'test_host_rhel_ovirt-vmconsole-host-sshd_is-faultless': 'RHEVM-19758',
        # rhevh tests ids
        'test_host_rhvh_vdsmd_running': 'RHEVM-19490',
        'test_host_rhvh_vdsmd_enabled': 'RHEVM-19491',
        'test_host_rhvh_vdsmd_is-faultless': 'RHEVM-19747',
        'test_host_rhvh_supervdsmd_running': 'RHEVM-19494',
        'test_host_rhvh_supervdsmd_enabled': 'RHEVM-19495',
        'test_host_rhvh_supervdsmd_is-faultless': 'RHEVM-19749',
        'test_host_rhvh_sanlock_running': 'RHEVM-19498',
        'test_host_rhvh_sanlock_enabled': 'RHEVM-19499',
        'test_host_rhvh_sanlock_is-faultless': 'RHEVM-19751',
        'test_host_rhvh_libvirtd_running': 'RHEVM-19502',
        'test_host_rhvh_libvirtd_enabled': 'RHEVM-19503',
        'test_host_rhvh_libvirtd_is-faultless': 'RHEVM-19753',
        'test_host_rhvh_mom-vdsm_running': 'RHEVM-19506',
        'test_host_rhvh_mom-vdsm_enabled': 'RHEVM-19507',
        'test_host_rhvh_mom-vdsm_is-faultless': 'RHEVM-19755',
        'test_host_rhvh_ovirt-imageio-daemon_running': 'RHEVM-19510',
        'test_host_rhvh_ovirt-imageio-daemon_enabled': 'RHEVM-19511',
        'test_host_rhvh_ovirt-imageio-daemon_is-faultless': 'RHEVM-19757',
        'test_host_rhvh_ovirt-vmconsole-host-sshd_running': 'RHEVM-19514',
        'test_host_rhvh_ovirt-vmconsole-host-sshd_enabled': 'RHEVM-19515',
        'test_host_rhvh_ovirt-vmconsole-host-sshd_is-faultless': 'RHEVM-19759',
    }

    @tier1
    @pytest.mark.parametrize(
        ("machine", "service", "action"),
        [
            polarion(polarion_map[i])(bz(bz_map[i])(arguments_dict[i]))
            for i in arguments_dict.keys()
        ]
    )
    def test_service(self, machine, service, action):
        """
        Test machine for service (running|enabled)

        Args:
            machine (str): type of machine (engine|host_rhel|host_rhvh)
            service (str): service that should be running or enabled
            action (bool): action to check (running|enabled)
        """
        machines = []
        if machine == "engine":
            machines = [config.ENGINE_HOST]
        elif machine == "host_rhel":
            machines = hosts_rhel
        elif machine == "host_rhvh":
            machines = hosts_rhvh
        else:
            pytest.skip(
                "Not implemented tests for machine type {}".format(machine)
            )
        if not machines:
            pytest.skip(
                "No suitable {} machines".format(machine)
            )

        for machine in machines:
            if action == "running":
                self.assert_service_is_running(
                    machine,
                    service
                )
            elif action == "enabled":
                self.assert_service_is_enabled(
                    machine,
                    service,
                    service not in config.DISABLED_SERVICES
                )
            elif action == "is-faultless":
                self.assert_service_is_faultless(
                    machine,
                    service
                )
            else:
                pytest.skip(
                    "Not implemented test for action type {}".format(action)
                )
