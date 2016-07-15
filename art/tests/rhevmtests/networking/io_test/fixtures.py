#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for IO_test
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import config as io_conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


class IO_fixture(NetworkFixtures):
    """
    Fixtures for io_test
    """
    pass


@pytest.fixture(scope="module")
def io_fixture_prepare_setup(request):
    """
    Prepare setup
    """
    io_fixture = IO_fixture()

    def fin1():
        """
        Finalizer for remove networks
        """
        io_fixture.remove_networks_from_setup(io_fixture.host_0_name)
    request.addfinalizer(fin1)

    io_fixture.prepare_networks_on_setup(
        networks_dict=io_conf.NET_DICT, dc=io_fixture.dc_0,
        cluster=io_fixture.cluster_0
    )


@pytest.fixture(scope="class")
def all_classes_teardown(request, io_fixture_prepare_setup):
    """
    Teardown fixture for all cases
    """

    def fin():
        """
        Remove networks from the host
        """
        network_helper.remove_networks_from_host()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case_09_fixture(request, all_classes_teardown):
    """
    Create network in data center with valid name
    """
    io_fixture = IO_fixture()
    initial_name = request.node.cls.initial_name

    local_dict = {
        initial_name: {}
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=io_fixture.dc_0, network_dict=local_dict
    )
