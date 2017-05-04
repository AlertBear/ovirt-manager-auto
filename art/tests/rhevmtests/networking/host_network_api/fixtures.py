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
        assert ll_hosts.update_host(
            positive=True, host=network_api.host_0_name,
            cluster=network_api.cluster_0
        )
    request.addfinalizer(fin)

    assert ll_hosts.update_host(
        positive=True, host=network_api.host_0_name,
        cluster=network_api_conf.SYNC_CL
    )


@pytest.fixture(scope="class")
def manage_ip_and_refresh_capabilities(request):
    """
    Set temporary IP on interface and refresh capabilities.
    """
    NetworkFixtures()
    host = conf.HOST_0_NAME
    for net, actual_ip, actual_netmask in (
        request.node.cls.manage_ip_list
    ):
        actual_netmask = actual_netmask or "24"
        testflow.setup(
            "Set temporary IP on %s with: IP=%s, Netmask=%s",
            net, actual_ip, actual_netmask
        )
        helper.manage_host_ip(
            interface=net, ip=actual_ip, netmask=actual_netmask
        )
    last_event = ll_events.get_max_event_id()
    testflow.setup("Refresh host %s capabilities", host)
    assert ll_hosts.refresh_host_capabilities(
        host=host, start_event_id=last_event
    )


@pytest.fixture(scope="class")
def reboot_host(request):
    """
    Reboot host
    """
    host = conf.HOSTS[2]
    vds = conf.VDS_HOSTS[2]
    testflow.setup("Reboot host %s", host)
    assert hl_hosts.deactivate_host_if_up(host=host, host_resource=vds)
    conf.VDS_0_HOST.add_power_manager(pm_type=conf.SSH_TYPE)
    conf.VDS_0_HOST.get_power_manager().restart()
    for is_connective in (False, True):
        conf.VDS_0_HOST.executor().wait_for_connectivity_state(
            positive=is_connective
        )

    assert hl_hosts.activate_host_if_not_up(host=host, host_resource=vds)


@pytest.fixture(scope="class")
def create_networks(request):
    """
    Create networks on datacenter
    """
    NetworkFixtures()
    networks = request.node.cls.networks

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=conf.HOSTS[2]
        )
    request.addfinalizer(fin)

    for k, v in networks.iteritems():
        networks = v.get("networks")
        datacenter = v.get("datacenter")
        cluster = v.get("cluster")
        testflow.setup("Create networks: %s", networks.keys())
        network_helper.prepare_networks_on_setup(
            networks_dict=networks, dc=datacenter, cluster=cluster
        )
