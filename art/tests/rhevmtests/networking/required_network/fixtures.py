#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for required_network
"""

import pytest

import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    networks as hl_networks
)
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.unittest_lib import testflow


@pytest.fixture(scope="class", autouse=True)
def activate_host(request):
    """
    Activate host if the host is not up
    """

    def fin():
        """
        Activate host if not up
        """
        assert hl_hosts.activate_host_if_not_up(host=conf.HOST_0_NAME)
    request.addfinalizer(fin)


@pytest.fixture(scope="class", autouse=True)
def create_network_on_setup(request):
    """
    Create network on setup
    """
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
        assert hl_networks.create_and_attach_networks(
            data_center=conf.DC_0, clusters=[conf.CL_0], networks=net_dict
        )
