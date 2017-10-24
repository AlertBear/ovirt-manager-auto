#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External Network Provider fixtures
"""

import shlex

import pytest

import config as enp_conf
import helper
import rhevmtests.config as global_config
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as net_config
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks, external_providers
)
from art.unittest_lib import testflow
from rhevmtests.networking import config_handler


@pytest.fixture(scope="module", autouse=True)
def check_running_on_rhevh(request):
    """
    Check if test is running on unsupported RHEVH environment

    TODO: remove fixture when RHV-H 4.2 is available for testing
    """
    env_rhevh_hosts = [
        h.name for h in global_config.HOSTS_RHEVH
        if h.name in net_config.HOSTS[:2]
    ]
    if env_rhevh_hosts:
        pytest.skip("Unsupported host(s) found: %s" % env_rhevh_hosts)


@pytest.fixture(scope="class")
def check_ldap_availability(request):
    """
    Check the availability of LDAP server
    """
    if not helper.check_ldap_availability(
        server=enp_conf.OVN_LDAP_DOMAIN, ports=enp_conf.OVN_LDAP_PORTS
    ):
        pytest.skip(
            "LDAP server: %s is unavailable" % enp_conf.OVN_LDAP_DOMAIN
        )


@pytest.fixture()
def add_ovn_provider(request):
    """
    Add OVN external network provider
    """
    provider_name = request.node.cls.provider_name

    def fin():
        """
        Remove OVN external network provider
        """
        testflow.teardown("Removing OVN network provider: %s", provider_name)
        assert enp_conf.OVN_PROVIDER.remove(provider_name)
    request.addfinalizer(fin)

    testflow.setup("Adding test network provider: %s", provider_name)
    enp_conf.OVN_EXTERNAL_PROVIDER_PARAMS["name"] = provider_name
    enp_conf.OVN_PROVIDER = external_providers.ExternalNetworkProvider(
        **enp_conf.OVN_EXTERNAL_PROVIDER_PARAMS
    )
    assert enp_conf.OVN_PROVIDER.add()


@pytest.fixture()
def configure_provider_plugin(request):
    """
    Configure provider authentication plugin
    """
    group_name = request.getfixturevalue("group")
    plugin = request.getfixturevalue("plugin")

    def fin():
        """
        Restore original configuration and restart ovirt-provider-ovn service
        """
        if enp_conf.OVN_CONFIG_FILE_BCK:
            testflow.teardown(
                "Restoring original provider package configuration"
            )
            assert not net_config.ENGINE_HOST.run_command(
                shlex.split(
                    enp_conf.OVN_CMD_CP_FILE.format(
                        src=enp_conf.OVN_CONFIG_FILE_BCK,
                        dst=enp_conf.OVN_CONFIG_FILE
                    )
                )
            )[0]
            testflow.teardown(
                "Restarting ovirt-provider-ovn and waiting for Keystone TCP "
                "service port"
            )
            helper.restart_service_and_wait(
                host=net_config.ENGINE_HOST, service="ovirt-provider-ovn",
                port=enp_conf.OVN_PROVIDER_KEYSTONE_PORT
            )
    request.addfinalizer(fin)

    testflow.setup(
        "Configuring OVN provider settings for %s group authentication", plugin
    )

    conf_handler = config_handler.HostConfigFileHandler(
        host=net_config.ENGINE_HOST, path=enp_conf.OVN_CONFIG_FILE
    )

    # Config file template
    params = enp_conf.OVN_AUTHENTICATION_BY_GROUP_CONF

    # Set authorization group name
    params["OVIRT"]["ovirt-admin-group-attribute-value"] = group_name

    # Save settings on OVN config file
    enp_conf.OVN_CONFIG_FILE_BCK = conf_handler.set_options(parameters=params)

    testflow.setup(
        "Restarting ovirt-provider-ovn and waiting for Keystone TCP service "
        "port"
    )
    assert helper.restart_service_and_wait(
        host=net_config.ENGINE_HOST, service="ovirt-provider-ovn",
        port=enp_conf.OVN_PROVIDER_KEYSTONE_PORT
    )


@pytest.fixture(scope="class")
def create_ovn_networks_on_provider(request):
    """
    Create OVN network(s) and subnet(s) on provider
    """
    add_networks = getattr(request.cls, "add_ovn_networks_to_provider", {})
    remove_networks = getattr(
        request.cls, "remove_ovn_networks_from_provider", {}
    )

    def fin():
        """
        Remove OVN networks and associated subnets
        """
        result_list = []
        networks_and_subnets = remove_networks or add_networks

        for net, subnet in networks_and_subnets.items():
            if subnet:
                subnet_name = subnet.get("name")
                testflow.teardown(
                    "Removing OVN subnet: %s from provider", subnet_name
                )
                result_list.append(
                    enp_conf.OVN_PROVIDER.remove_subnet(
                        subnet_name=subnet_name
                    )
                )

            testflow.teardown("Removing OVN network: %s from provider", net)
            result_list.append(
                enp_conf.OVN_PROVIDER.remove_network(network_name=net)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for net, subnet in add_networks.items():
        txt = " with subnet: %s" % subnet.get("name") if subnet else ""
        testflow.setup("Adding network: %s%s to OVN provider", net, txt)
        assert enp_conf.OVN_PROVIDER.add_network(
            network_name=net, subnet_dict=subnet
        )


@pytest.fixture(scope="class")
def import_ovn_networks(request):
    """
    Import OVN network(s)
    """
    import_networks = getattr(request.cls, "import_ovn_networks_to_engine", [])
    remove_networks = getattr(
        request.cls, "remove_ovn_networks_from_engine", []
    )
    dc = request.node.cls.dc
    cluster = request.node.cls.cl

    def fin():
        """
        Remove OVN network(s)
        """
        results_list = []
        networks = remove_networks or import_networks

        for net in [net for net in networks if ll_networks.find_network(net)]:
            testflow.teardown("Removing network: %s from engine", net)
            results_list.append(
                ll_networks.remove_network(positive=True, network=net)
            )
        assert all(results_list)
    request.addfinalizer(fin)

    for net in import_networks:
        testflow.setup(
            "Importing network: %s from OVN network provider to DC: %s "
            "Cluster: %s", net, dc, cluster
        )
        assert enp_conf.OVN_PROVIDER.import_network(
            network=net, datacenter=dc, cluster=cluster
        )


@pytest.fixture(scope="class")
def remove_ifcfg_from_vms(request):
    """
    Remove ifcfg file from VM(s)
    """
    def fin():
        """
        Remove ifcfg file from VM
        """
        testflow.teardown("Removing ifcfg files from running VM's")
        vms_resources = [
            rsc for rsc in enp_conf.OVN_VMS_RESOURCES.values() if rsc
        ]
        assert network_helper.remove_ifcfg_files(vms_resources=vms_resources)
    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def configure_ovn(request):
    """
    1. Configure ovirt-provider-ovn-driver component on OVN hosts 1 and 2
    2. Verify that firewalld service is stopped on OVN hosts_1 and 2 until
       RFE: https://bugzilla.redhat.com/show_bug.cgi?id=1432354 is resolved.
    3. Verify that firewalld is running on OVN central
    """
    ovn_central = net_config.ENGINE_HOST
    ovn_hosts = net_config.VDS_HOSTS_LIST[:2]

    def fin():
        """
        Restore firewalld service state on OVN hosts
        """
        results = []

        for host in enp_conf.OVN_FIREWALLD_STARTED_SERVERS:
            testflow.setup(
                "Starting firewall firewalld service on host: %s", host.fqdn
            )
            results.append(
                (
                    helper.service_handler(
                        host=host, service="firewalld", action="start"
                    ),
                    "Failed to start firewalld service on host: %s"
                    % host.fqdn
                )
            )
            results.append(
                (
                    helper.service_handler(
                        host=host, service="libvirtd", action="restart"
                    ),
                    "Failed to restart libvirtd service on host: %s"
                    % host.fqdn
                )
            )

        global_helper.raise_if_false_in_list(results)
    request.addfinalizer(fin)

    # OVN central configuration
    testflow.setup(
        "Verifying that firewalld is started on OVN central: %s",
        ovn_central.fqdn
    )
    assert helper.service_handler(
        host=ovn_central, service="firewalld", action="active"
    )

    # OVN driver configuration
    for host in ovn_hosts:
        # Stop firewall services that blocks OVN traffic
        testflow.setup(
            "Checking if firewalld is started on OVN host: %s", host.fqdn
        )
        if helper.service_handler(
            host=host, service="firewalld", action="active"
        ):
            testflow.setup(
                "Stopping firewall firewalld service on host: %s", host.fqdn
            )
            assert helper.service_handler(host=host, service="firewalld")

            testflow.setup(
                "Restarting libvirtd service on host: %s", host.fqdn
            )
            assert helper.service_handler(
                host=host, service="libvirtd", action="restart"
            )
            enp_conf.OVN_FIREWALLD_STARTED_SERVERS.append(host)

        # Start ovn-controller
        # TODO: removed once BZ:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1490104 is resolved
        if not helper.service_handler(
            host=host, service=enp_conf.OVN_CONTROLLER_SERVICE, action="active"
        ):
            testflow.setup(
                "Starting ovn-controller service on host: %s", host.fqdn
            )
            assert host.service(name=enp_conf.OVN_CONTROLLER_SERVICE).start()

        testflow.setup("Configuring vdsm-tool on host: %s", host.fqdn)
        assert not host.run_command(
            shlex.split(
                enp_conf.OVN_CMD_VDSM_TOOL.format(
                    provider_ip=ovn_central.ip, host_ip=host.ip
                )
            )
        )[0]


@pytest.fixture(scope="class")
def get_default_ovn_provider(request):
    """
    Get the default OVN network provider from engine and save its instance
    """
    provider = request.node.cls.provider_name

    testflow.setup("Getting default provider: %s from engine", provider)
    assert helper.get_provider_from_engine(provider_name=provider)


@pytest.fixture(scope="class")
def setup_vms_ovn_interface(request):
    """
    1. Set IP(s) on the non-mgmt interface of VM(s)
    2. Set MTU 1400 on the non-mgmt interface of the VM(s)
    """
    for vm_name, net in request.node.cls.set_vms_ips.items():
        testflow.setup("Setting IP network: %s on VM: %s", net, vm_name)
        assert helper.set_ip_non_mgmt_nic(vm=vm_name, ip_network=net)

        # On OVN tunnel connections, MTU should be set to 1400 for TCP transfer
        # to work successfully over tunnel
        testflow.setup("Setting MTU 1400 on VM: %s OVN interface", vm_name)
        assert helper.set_vm_non_mgmt_interface_mtu(
            vm=enp_conf.OVN_VMS_RESOURCES[vm_name], mtu=1400
        )


@pytest.fixture(scope="class")
def save_vm_resources(request):
    """
    Save VM(s) host resources
    """
    for vm_name in request.node.cls.save_vm_resources_params:
        testflow.setup("Saving VM: %s host resource", vm_name)
        enp_conf.OVN_VMS_RESOURCES[vm_name] = global_helper.get_vm_resource(
            vm=vm_name, start_vm=False
        )
        assert enp_conf.OVN_VMS_RESOURCES[vm_name], (
            "Unable to get VM: %s host resource" % vm_name
        )


@pytest.fixture(scope="class")
def benchmark_file_transfer(request):
    """
    Benchmark Host-to-Host file transfer rate and collect performance counters
    from hosts
    """
    testflow.setup(
        "Benchmarking file transfer from host: %s to host: %s",
        net_config.HOST_0_NAME, net_config.HOST_1_NAME
    )
    copy_file_res, perf_counters = helper.copy_file_benchmark(
        src_host=net_config.VDS_0_HOST, dst_host=net_config.VDS_1_HOST,
        dst_ip=net_config.HOST_1_IP, size=1000
    )
    assert copy_file_res[0], "Failed to copy file over OVN tunnel"

    # Save counters
    enp_conf.OVN_HOST_PERF_COUNTERS = (
        perf_counters[0], perf_counters[1], copy_file_res[1]
    )
    # Reset collection values
    enp_conf.COLLECT_PERFORMANCE_FLAGS = [True, True]
