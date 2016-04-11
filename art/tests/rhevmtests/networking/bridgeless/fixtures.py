#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for bridgeless
"""

import pytest

import rhevmtests.networking.config as conf
import rhevmtests.networking.bridgeless.helper as bridgeless_helper
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class BridgeLess(NetworkFixtures):
    """
    Prepare setup for bridgeless
    """

    def remove_networks_from_host(self):
        """
        Remove networks from host
        """
        network_helper.remove_networks_from_host()


@pytest.fixture(scope="module")
def bridgeless_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    bridgeless = BridgeLess()

    def fin2():
        """
        Finalizer for remove dummies
        """
        bridgeless.remove_dummies(host_resource=bridgeless.vds_0_host)
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove networks
        """
        bridgeless.remove_networks_from_setup(
            hosts=bridgeless.host_0_name
        )
    request.addfinalizer(fin1)

    bridgeless.prepare_dummies(
        host_resource=bridgeless.vds_0_host,
        num_dummy=bridgeless.num_dummies
    )
    bridgeless.prepare_networks_on_setup(
        networks_dict=conf.BRIDGELESS_NET_DICT, dc=bridgeless.dc_0,
        cluster=bridgeless.cluster_0
    )


@pytest.fixture(scope="class")
def all_classes_teardown(request):
    """
    Teardown fixture for all cases
    """
    bridgeless = BridgeLess()

    def fin():
        """
        Remove networks
        """
        bridgeless.remove_networks_from_host()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case_03_fixture(request, all_classes_teardown, bridgeless_prepare_setup):
    """
    Fixture for case03
    """
    bridgeless = BridgeLess()
    bridgeless_helper.create_networks_on_host(
        nic=bridgeless.bond_0, slaves=conf.DUMMYS[:2]
    )


@pytest.fixture(scope="class")
def case_04_fixture(request, all_classes_teardown, bridgeless_prepare_setup):
    """
    Fixture for case03
    """
    bridgeless = BridgeLess()
    bridgeless_helper.create_networks_on_host(
        nic=bridgeless.bond_1, slaves=conf.DUMMYS[2:4]
    )
