#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for required_network
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.helper as network_helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class", autouse=True)
def activate_host(request):
    """
    Activate host if the host is not up
    """
    required_network = NetworkFixtures()

    def fin():
        """
        Activate host if not up
        """
        testflow.teardown("Activate host %s", required_network.host_0_name)
        hl_hosts.activate_host_if_not_up(host=required_network.host_0_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class", autouse=True)
def create_network_on_setup(request):
    """
    Create network on setup
    """
    required_network = NetworkFixtures()
    net_dict = getattr(request.node.cls, "net_dict", dict())

    def fin():
        """
        Remove network from setup
        """
        if net_dict:
            net = net_dict.keys()[0]
            testflow.teardown("Remove network %s", net)
            assert ll_networks.remove_network(positive=True, network=net)
    request.addfinalizer(fin)

    if net_dict:
        network_helper.prepare_networks_on_setup(
            networks_dict=net_dict, dc=required_network.dc_0,
            cluster=required_network.cluster_0
        )
