#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_api
"""

import pytest

import config as network_api_conf
import helper
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    events as ll_events,
    hosts as ll_hosts
)
from art.unittest_lib import testflow
import rhevmtests.networking.config as conf


@pytest.fixture(scope="class")
def remove_network(request):
    """
    Remove network.
    """
    nets_to_remove = request.node.cls.nets_to_remove
    assert hl_networks.remove_networks(
        positive=True, networks=nets_to_remove, data_center=conf.DC_0
    )


@pytest.fixture(scope="class")
def update_host_to_another_cluster(request):
    """
    Update host to another cluster.
    """
    def fin():
        """
        Move host to original cluster.
        """
        assert ll_hosts.update_host(
            positive=True, host=conf.HOST_0_NAME, cluster=conf.CL_0
        )
    request.addfinalizer(fin)

    assert ll_hosts.update_host(
        positive=True, host=conf.HOST_0_NAME, cluster=network_api_conf.SYNC_CL
    )


@pytest.fixture(scope="class")
def manage_ip_and_refresh_capabilities(request):
    """
    Set temporary IP on interface and refresh capabilities.
    """
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
    conf.VDS_0_HOST.add_power_manager(pm_type=conf.SSH_TY)
    conf.VDS_0_HOST.get_power_manager().restart()
    for is_connective in (False, True):
        conf.VDS_0_HOST.executor().wait_for_connectivity_state(
            positive=is_connective
        )

    assert hl_hosts.activate_host_if_not_up(host=host, host_resource=vds)
