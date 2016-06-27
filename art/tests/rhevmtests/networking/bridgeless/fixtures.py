#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for bridgeless
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


@pytest.fixture(scope="class")
def case_01_fixture(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    bridgeless = NetworkFixtures()
    bond_1 = request.node.cls.bond_1
    bond_2 = request.node.cls.bond_2

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
        bridgeless.remove_networks_from_setup(hosts=bridgeless.host_0_name)
    request.addfinalizer(fin1)

    bridgeless.prepare_dummies(
        host_resource=bridgeless.vds_0_host, num_dummy=bridgeless.num_dummies
    )

    bridgeless.prepare_networks_on_setup(
        networks_dict=conf.BRIDGELESS_NET_DICT, dc=bridgeless.dc_0,
        cluster=bridgeless.cluster_0
    )

    local_dict = {
        "add": {
            "1": {
                "slaves": conf.DUMMYS[:2],
                "nic": bond_1,
            },
            "2": {
                "slaves": conf.DUMMYS[2:4],
                "nic": bond_2
            },
        }
    }

    assert hl_host_network.setup_networks(
        host_name=bridgeless.host_0_name, **local_dict
    )
