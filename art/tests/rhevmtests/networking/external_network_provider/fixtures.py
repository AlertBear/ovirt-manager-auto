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
import rhevmtests.networking.config as net_config
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_exceptions
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms,
    external_providers
)
from art.rhevm_api.utils import config_handler
from art.unittest_lib import testflow


@pytest.fixture(scope="module", autouse=True)
def check_running_on_rhevh(request):
    """
    Check if test is running on unsupported environment
    """
    # TODO: remove this fixture when RHV-H support will be added
    for host in net_config.VDS_HOSTS_LIST[:2]:
        testflow.setup(
            "Checking RHV host: %s compatibility with tests", host.fqdn
        )
        if host.os.distribution.distname == global_config.RHVH:
            pytest.skip(
                "Unsupported host found: %s" % net_config.VDS_0_HOST.fqdn
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
def remove_ovn_networks_from_provider(request):
    """
    Remove OVN network(s) and associated subnet(s) from provider
    """
    def fin():
        """
        Remove OVN networks and associated subnets
        """
        result_list = list()

        for name, subnet in enp_conf.OVN_NETS.iteritems():
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

            testflow.teardown("Removing OVN network: %s from provider", name)
            result_list.append(
                enp_conf.OVN_PROVIDER.remove_network(network_name=name)
            )
        assert all(result_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_ovn_networks_from_engine(request):
    """
    Remove OVN networks from engine
    """
    networks = enp_conf.OVN_NET_NAMES

    def fin():
        """
        Remove OVN networks
        """
        results_list = list()

        for net in [net for net in networks if ll_networks.find_network(net)]:
            testflow.teardown("Removing network: %s from engine", net)
            results_list.append(
                ll_networks.remove_network(positive=True, network=net)
            )
        assert all(results_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnics_from_vms(request):
    """
    Remove vNIC(s) with properties from VM(s)
    """
    vnics_remove_dict = request.node.cls.remove_vnics_from_vms_params

    def fin():
        """
        Remove vNIC from VM
        """
        results_list = list()

        for vm, vnic in vnics_remove_dict.iteritems():
            testflow.teardown("Removing vNIC: %s from VM: %s", vnic, vm)
            try:
                res = ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
            except apis_exceptions.EntityNotFound:
                res = True
            results_list.append(res)
        assert all(results_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profile(s)
    """
    vnic_profiles = request.node.cls.remove_vnic_profiles_params

    def fin():
        """
        Remove vNIC profile
        """
        results = list()

        for name, net in vnic_profiles.iteritems():
            testflow.teardown("Removing vNIC profile: %s", name)
            if ll_networks.is_vnic_profile_exist(name):
                results.append(
                    ll_networks.remove_vnic_profile(
                        positive=True, vnic_profile_name=name, network=net
                    )
                )
        assert all(results)
    request.addfinalizer(fin)


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
    Prepare the environment for OVN tests

    OVN provider driver (OVN node) will be configured in a two nodes topology,
    on servers: vds_1 and vds_2
    """
    provider_server = net_config.ENGINE_HOST
    provider_driver_servers = net_config.VDS_HOSTS_LIST[:2]
    all_servers = [provider_server] + provider_driver_servers

    def fin():
        """
        Stopping OVN service on driver servers
        """
        for host in provider_driver_servers:
            testflow.teardown(
                "Stopping service: %s on OVN driver server: %s",
                enp_conf.OVN_DRIVER_SERVICE, host.fqdn
            )
            assert helper.service_handler(
                host=host, service=enp_conf.OVN_DRIVER_SERVICE
            ), "Failed to stop service: %s" % enp_conf.OVN_DRIVER_SERVICE
    request.addfinalizer(fin)

    # Configuration actions for all servers
    for host in all_servers:
        # Stop firewall services that blocks OVN traffic.
        # Waiting for RFE: https://bugzilla.redhat.com/show_bug.cgi?id=1432354
        # to be resolved.
        for service in enp_conf.OVN_FW_SERVICES:
            testflow.setup(
                "Stopping firewall service: %s on host: %s", service, host.fqdn
            )
            assert helper.service_handler(host=host, service=service)

    # Driver server configuration
    for host in provider_driver_servers:
        testflow.setup("Starting OVN driver service on host: %s", host.fqdn)
        assert host.service(name=enp_conf.OVN_DRIVER_SERVICE).start()

        testflow.setup("Configuring vdsm-tool on host: %s", host.fqdn)
        assert not host.run_command(
            shlex.split(
                enp_conf.OVN_CMD_VDSM_TOOL.format(
                    provider_ip=provider_server.ip, host_ip=host.ip
                )
            )
        )[0]
