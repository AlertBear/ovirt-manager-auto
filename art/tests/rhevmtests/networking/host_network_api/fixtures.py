#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_api
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import config as network_api_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def remove_network(request):
    """
    Remove network.
    """
    network_api = NetworkFixtures()
    nets_to_remove = request.node.cls.nets_to_remove
    testflow.setup("Remove networks %s", nets_to_remove)
    assert hl_networks.remove_networks(
        positive=True, networks=nets_to_remove, data_center=network_api.dc_0
    )


@pytest.fixture(scope="class")
def update_host_to_another_cluster(request):
    """
    Update host to another cluster.
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Move host to original cluster.
        """
        testflow.teardown(
            "Move host %s to original cluster %s", network_api.host_0_name,
            network_api.cluster_0
        )
        assert ll_hosts.updateHost(
            positive=True, host=network_api.host_0_name,
            cluster=network_api.cluster_0
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Update host %s to cluster %s", network_api.host_0_name,
        network_api_conf.SYNC_CL
    )
    assert ll_hosts.updateHost(
        positive=True, host=network_api.host_0_name,
        cluster=network_api_conf.SYNC_CL
    )


@pytest.fixture(scope="class")
def manage_ip_and_refresh_capabilities(request):
    """
    Set temporary IP on interface and refresh capabilities.
    """
    NetworkFixtures()
    for net, actual_ip, actual_netmask, set_ip in (
        request.node.cls.manage_ip_list
    ):
        testflow.setup(
            "Set temporary IP %s on interface %s",
            actual_ip, net
        )
        if not actual_netmask:
            actual_netmask = "24"

        helper.manage_host_ip(
            interface=net, ip=actual_ip, netmask=actual_netmask, set_ip=set_ip
        )
    last_event = ll_events.get_max_event_id()
    testflow.setup("Refresh host %s capabilities", conf.HOST_0_NAME)
    ll_hosts.refresh_host_capabilities(
        host=conf.HOST_0_NAME, start_event_id=last_event
    )


@pytest.fixture(scope="class")
def reboot_host(request):
    """
    Reboot host
    """
    host = conf.HOST_0_NAME
    testflow.setup("Reboot host %s", host)
    assert hl_hosts.deactivate_host_if_up(host=host)
    conf.VDS_0_HOST.add_power_manager(pm_type=conf.SSH_TYPE)
    conf.VDS_0_HOST.get_power_manager().restart()
    for is_connective in (False, True):
        conf.VDS_0_HOST.executor().wait_for_connectivity_state(
            positive=is_connective
        )

    assert hl_hosts.activate_host_if_not_up(host=host)


@pytest.fixture(scope="class", autouse=True)
def create_networks(request):
    """
    Create networks on datacenter
    """
    network_api = NetworkFixtures()
    networks = request.node.cls.networks

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=network_api.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Create networks: %s", networks.keys())
    network_helper.prepare_networks_on_setup(
        networks_dict=networks, dc=network_api.dc_0,
        cluster=network_api.cluster_0
    )
