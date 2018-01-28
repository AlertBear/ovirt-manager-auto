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
    clusters as ll_clusters,
    hosts as ll_hosts,
    external_providers
)
from art.unittest_lib import testflow
from rhevmtests.networking import config_handler


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


@pytest.fixture(scope="class")
def remove_unmanaged_provider(request):
    """
    Remove unmanaged external network provider
    """
    provider_name_to_remove = request.node.cls.remove_provider_name

    def fin():
        """
        Remove unmanaged external network provider
        """
        if provider_name_to_remove:
            assert enp_conf.UNMANAGED_PROVIDER.remove(provider_name_to_remove)
    request.addfinalizer(fin)


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
    Create OVN network(s) and subnet(s) on provider and wait for auto-sync
        changes
    """
    add_networks = getattr(request.cls, "add_ovn_networks_to_provider", {})
    remove_networks = getattr(
        request.cls, "remove_ovn_networks_from_provider", {}
    )
    networks_and_subnets = remove_networks or add_networks

    def fin2():
        """
        Wait for auto-sync changes
        """
        assert helper.wait_for_auto_sync(networks=networks_and_subnets.keys())
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove OVN networks and associated subnets
        """
        result_list = []

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
    request.addfinalizer(fin1)

    for net, subnet in add_networks.items():
        txt = " with subnet: %s" % subnet.get("name") if subnet else ""
        testflow.setup("Adding network: %s%s to OVN provider", net, txt)
        assert enp_conf.OVN_PROVIDER.add_network(
            network_name=net, subnet_dict=subnet
        )

    assert helper.wait_for_auto_sync(
        networks=add_networks.keys(), removal=False
    )


@pytest.fixture(scope="module")
def set_auto_sync_time(request):
    """
    Set auto-sync sync cycle rate
    """
    sync_rate_key = "ExternalNetworkProviderSynchronizationRate"
    auto_sync_rate = "%s={rate}" % sync_rate_key
    save_rate = ""

    def fin():
        """
        Restore auto-sync rate on engine
        """
        testflow.teardown(
            "Restoring auto-sync cycle rate value to %s", save_rate
        )
        assert net_config.ENGINE.engine_config(
            action="set",
            param=auto_sync_rate.format(rate=save_rate), restart=True
        ).get("results")
    request.addfinalizer(fin)

    testflow.setup("Getting current auto-sync cycle rate value")
    results = net_config.ENGINE.engine_config(
        action="get", param=sync_rate_key, restart=False
    ).get("results")
    assert results
    save_rate = results.get(sync_rate_key, {}).get("value", None)
    assert save_rate

    testflow.setup(
        "Setting auto-sync cycle rate value to %s", enp_conf.AUTO_SYNC_RATE
    )
    assert net_config.ENGINE.engine_config(
        action="set",
        param=auto_sync_rate.format(rate=enp_conf.AUTO_SYNC_RATE), restart=True
    ).get("results")


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


@pytest.fixture(scope="class")
def set_cluster_external_network_provider(request):
    """
    Set cluster CL_0 external network provider
    """
    cl = request.node.cls.cl

    def fin():
        """
        Set default external network provider
        """
        assert ll_clusters.updateCluster(
            positive=True, cluster=cl, external_network_provider=""
        )
    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True, cluster=cl,
        external_network_provider=enp_conf.OVN_PROVIDER_NAME
    )


@pytest.fixture(scope="class")
def reinstall_hosts(request):
    """
    Reinstall host(s) to trigger OVN host-deploy (ansible)
    """
    hosts_to_reinstall = getattr(request.cls, "hosts_to_reinstall", [])

    for host_idx in hosts_to_reinstall:
        host_name = net_config.HOSTS_LIST[host_idx]
        assert ll_hosts.deactivate_host(positive=True, host=host_name)
        assert ll_hosts.install_host(
            host=host_name, root_password=global_config.VDC_ROOT_PASSWORD,
            external_network_provider=enp_conf.OVN_PROVIDER_NAME
        )
        assert ll_hosts.activate_host(positive=True, host=host_name)


@pytest.fixture(scope="class")
def get_default_ovn_provider(request):
    """
    1. Login with the default admin to get a token
    2. Get the default OVN network provider
    3. Test connection to the provider (optionally)
    """
    provider = request.node.cls.provider_name
    test_conn = getattr(request.cls, "test_provider_connection", False)

    testflow.setup("Getting default provider: %s from engine", provider)
    enp_conf.OVN_PROVIDER = helper.get_provider_from_engine(
        provider_name=provider,
        keystone_user=global_config.VDC_ADMIN_JDBC_LOGIN,
        keystone_pass=global_config.VDC_PASSWORD
    )
    if test_conn:
        testflow.setup("Testing connection to the provider: %s", provider)
        assert enp_conf.OVN_PROVIDER.test_connection()


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
    from hosts to be used as baseline for the tests
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


@pytest.fixture(scope="class")
def skip_10g_env(request):
    """
    Skip test if 10GBE interface exists on one of the first two hosts in
        the env
    """
    for host in net_config.VDS_HOSTS_LIST[:2]:
        mgmt_iface = host.network.find_int_by_bridge("ovirtmgmt")
        iface_speed = host.network.get_interface_speed(interface=mgmt_iface)
        assert iface_speed, (
            "Failed to get interface: %s speed on host: %s"
            % (mgmt_iface, host.fqdn)
        )
        if int(iface_speed) >= 10000:
            pytest.skip(
                "NIC: %s on host: %s is unsupported on this test, we have "
                "bandwidth performance issue with 10GBE for now."
                % (mgmt_iface, host.fqdn)
            )
