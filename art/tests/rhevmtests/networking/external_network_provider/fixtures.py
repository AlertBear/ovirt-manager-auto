#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External Network Provider fixtures
"""

import shlex

import pytest

import art.core_api.apis_exceptions as api_exceptions
import config as enp_conf
import helper
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms,
    external_providers
)
from art.unittest_lib import testflow
from rhevmtests import (
    config as conf,
    helpers as global_helper
)
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def remove_ovn_provider(request):
    """
    Remove OVN provider from engine
    """
    NetworkFixtures()
    name = enp_conf.OVN_PROVIDER_NAME

    def fin():
        testflow.teardown("Removing OVN external network provider: %s", name)
        assert enp_conf.OVN_PROVIDER.remove(openstack_ep=name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_ovn_networks_from_provider(request):
    """
    Remove OVN network(s) and associated subnet(s) from provider
    """
    NetworkFixtures()

    def fin():
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
    NetworkFixtures()
    networks = enp_conf.OVN_NET_NAMES

    def fin():
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
    NetworkFixtures()
    vnics_remove_dict = request.node.cls.remove_vnics_from_vms_params

    def fin():
        results_list = list()

        for vm, vnic in vnics_remove_dict.iteritems():
            testflow.teardown("Removing vNIC: %s from VM: %s", vnic, vm)
            try:
                res = ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
            except api_exceptions.EntityNotFound:
                res = True
            results_list.append(res)
        assert all(results_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profile(s)
    """
    NetworkFixtures()
    vnic_profiles = request.node.cls.remove_vnic_profiles_params

    def fin():
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
    NetworkFixtures()

    def fin():
        testflow.teardown("Removing ifcfg files from running VM's")
        vms_resources = [
            rsc for rsc in enp_conf.OVN_VMS_RESOURCES.values() if rsc
        ]
        assert network_helper.remove_ifcfg_files(vms_resources=vms_resources)
    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def deploy_ovn(request):
    """
    Deploy OVN provider feature components: OVN provider, OVN provider driver
    and all the required OVN and OVS dependencies

    OVN provider (OVN central server) will be installed on the oVirt engine
    OVN provider driver (OVN node) will be installed in a two nodes topology,
    on servers: vds_1 and vds_2
    """
    ovn = NetworkFixtures()

    provider_server = conf.ENGINE_HOST
    provider_driver_servers = ovn.vds_list
    all_servers = [provider_server] + provider_driver_servers
    results = list()

    def fin7():
        """
        Check if one of the finalizers failed
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin7)

    def fin6():
        """
        Restore stopped services on all servers
        """
        for host, services in enp_conf.OVN_SERVICES_RUNNING.iteritems():
            for service in services:
                testflow.teardown(
                    "Restoring service: %s state on host: %s",
                    service, host.fqdn
                )
                results.append(
                    (
                        helper.service_handler(
                            host=host, service=service, action="start"
                        ), "Failed to restore service: %s state" % service
                    )
                )
    request.addfinalizer(fin6)

    def fin5():
        """
        Removing OVN bridge from provider driver servers
        """
        for host in provider_driver_servers:
            if host.fs.exists(enp_conf.OVN_BRIDGE_INTERFACE_FILE):
                testflow.teardown(
                    "Removing OVN bridge from host: %s", host.fqdn
                )
                results.append(
                    (
                        not host.run_command(
                            shlex.split(enp_conf.OVN_CMD_DEL_OVN_BRIDGE)
                        )[0],
                        "Failed to remove OVN bridge from host: %s" % host.fqdn
                    )
                )
    request.addfinalizer(fin5)

    def fin4():
        """
        Removing OVN packages from provider server
        """
        for rpm_name in enp_conf.OVN_PROVIDER_REMOVE_RPMS:
            testflow.teardown(
                "Removing OVN package: %s from OVN provider server: %s",
                rpm_name, provider_server.fqdn
            )
            results.append(
                (
                    provider_server.package_manager.remove(package=rpm_name),
                    "Failed to remove OVN package: %s" % rpm_name
                )
            )
    request.addfinalizer(fin4)

    def fin3():
        """
        Stopping OVN service on provider server
        """
        testflow.teardown(
            "Stopping OVN service: %s on OVN provider: %s",
            enp_conf.OVN_PROVIDER_SERVICE, provider_server.fqdn
        )
        helper.service_handler(
            host=host, service=enp_conf.OVN_PROVIDER_SERVICE
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Removing OVN packages from driver servers
        """
        for host in provider_driver_servers:
            for rpm_name in enp_conf.OVN_DRIVER_REMOVE_RPMS:
                testflow.teardown(
                    "Removing OVN package: %s from OVN driver driver: %s",
                    rpm_name, host.fqdn
                )
                results.append(
                    (
                        host.package_manager.remove(package=rpm_name),
                        "Failed to remove OVN package: %s" % rpm_name
                    )
                )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stopping OVN service on driver servers
        """
        for host in provider_driver_servers:
            testflow.teardown(
                "Stopping service: %s on OVN driver server: %s",
                enp_conf.OVN_DRIVER_SERVICE, host.fqdn
            )
            results.append(
                (
                    helper.service_handler(
                        host=host, service=enp_conf.OVN_DRIVER_SERVICE
                    ),
                    "Failed to stop service: %s" % enp_conf.OVN_DRIVER_SERVICE
                )
            )
    request.addfinalizer(fin1)

    # Deployment actions for all servers
    for host in all_servers:
        # Stop firewall services that blocks OVN traffic as a workaround for BZ
        # ticket: https://bugzilla.redhat.com/show_bug.cgi?id=1390938
        for service in enp_conf.OVN_FW_SERVICES:
            testflow.setup(
                "Stopping firewall service: %s on host: %s", service, host.fqdn
            )
            assert helper.service_handler(host=host, service=service)

        for service in enp_conf.OVN_SERVICES_TO_STOP_AND_START:
            state = helper.service_handler(
                host=host, service=service, action="state"
            )
            if state:
                testflow.setup(
                    "Saving service: %s is-active state: %s on host: %s",
                    service, state, host
                )
                if host not in enp_conf.OVN_SERVICES_RUNNING:
                    enp_conf.OVN_SERVICES_RUNNING[host] = list()
                enp_conf.OVN_SERVICES_RUNNING[host].append(service)

    # OVN provider deployment
    testflow.setup(
        "Installing OVN provider packages: %s on host: %s",
        enp_conf.OVN_PROVIDER_RPM, provider_server.fqdn
    )
    assert helper.rpm_install(
        host=provider_server, rpm_name=enp_conf.OVN_PROVIDER_RPM
    )

    testflow.setup(
        "Reloading systemd daemon on host: %s", provider_server.fqdn
    )
    assert not provider_server.run_command(
        shlex.split(enp_conf.OVN_CMD_SYSD_RELOAD)
    )[0]

    testflow.setup("Starting OVN provider on host: %s", provider_server.fqdn)
    assert provider_server.service(
        name=enp_conf.OVN_PROVIDER_SERVICE
    ).start()

    # OVN driver deployment
    for host in provider_driver_servers:
        testflow.setup(
            "Installing OVN controller packages: %s on host: %s",
            enp_conf.OVN_DRIVER_RPM, host.fqdn
        )
        assert helper.rpm_install(host=host, rpm_name=enp_conf.OVN_DRIVER_RPM)

        testflow.setup("Reloading systemd daemon on host %s", host.fqdn)
        assert not host.run_command(
            shlex.split(enp_conf.OVN_CMD_SYSD_RELOAD)
        )[0]

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

    # Initialize OVN provider class
    enp_conf.OVN_PROVIDER = external_providers.ExternalNetworkProvider(
        **enp_conf.OVN_EXTERNAL_PROVIDER_PARAMS
    )

    # Check for existing OVN objects in the DB
    helper.check_for_ovn_objects()
