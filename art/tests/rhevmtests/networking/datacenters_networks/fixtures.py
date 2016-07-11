#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for datacenter networks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class DatacenterNetworks(NetworkFixtures):
    """
    Fixtures for datacenter networks
    """
    def __init__(self):
        super(DatacenterNetworks, self).__init__()
        self.dc_networks_1 = conf.DATACENTER_NETWORKS_DC_NAMES[1]
        self.dc_0_prefix = "dc_0_net"
        self.dc_1_prefix = "dc_1_net"

    def delete_networks_in_dc(self, dc):
        """
        Delete networks in datacenter

        Args:
            dc (str): Datacenter name

        Raises:
            AssertionError: If delete failed
        """
        assert ll_networks.delete_networks_in_datacenter(
            datacenter=dc, mgmt_net=self.mgmt_bridge
        )

    def create_networks_in_dc(self, nets_num, dc, prefix):
        """
        Create networks in datacenter

        Args:
            nets_num (int): Number of networks to create
            dc (str): Datacenter name
            prefix (str): Networks prefix name

        Raises:
            AssertionError: If create fails
        """
        dc_net_list = ll_networks.create_networks_in_datacenter(
            num_of_net=nets_num, datacenter=dc, prefix=prefix
        )

        if self.dc_0_prefix == prefix:
            conf.DC_0_NET_LIST = dc_net_list

        if self.dc_1_prefix == prefix:
            conf.DC_1_NET_LIST = dc_net_list

        assert dc_net_list


@pytest.fixture(scope="module")
def datacenter_networks_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    dc_net = DatacenterNetworks()

    def fin():
        """
        Finalizer for remove basic setup
        """
        hl_networks.remove_basic_setup(
            datacenter=dc_net.dc_networks_1
        )
    request.addfinalizer(fin)

    assert hl_networks.create_basic_setup(
        datacenter=dc_net.dc_networks_1, version=conf.COMP_VERSION
    )


@pytest.fixture(scope="class")
def teardown_all_cases(request, datacenter_networks_prepare_setup):
    """
    Teardown for all cases
    """
    dc_net = DatacenterNetworks()

    def fin():
        """
        Finalizer for remove networks from setup
        """
        dc_net.delete_networks_in_dc(dc=dc_net.dc_0)
        dc_net.delete_networks_in_dc(dc=dc_net.dc_networks_1)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_01(request, teardown_all_cases):
    """
    Fixture for case01
    """
    dc_net = DatacenterNetworks()
    dc_net.create_networks_in_dc(
        nets_num=10, dc=dc_net.dc_0, prefix=dc_net.dc_0_prefix
    )
    dc_net.create_networks_in_dc(
        nets_num=5, dc=dc_net.dc_networks_1, prefix=dc_net.dc_1_prefix
    )


@pytest.fixture(scope="class")
def fixture_case_02(request, teardown_all_cases):
    """
    Fixture for case02
    """
    dc_net = DatacenterNetworks()
    for key, val in conf.DATACENTER_NETWORKS_NET_DICT.iteritems():
        name = "_".join([ll_networks.NETWORK_NAME, key])
        kwargs_dict = {
            key: val,
            "name": name
        }
        assert ll_networks.create_network_in_datacenter(
            positive=True, datacenter=dc_net.dc_networks_1, **kwargs_dict
        )


@pytest.fixture(scope="class")
def fixture_case_03(request, teardown_all_cases):
    """
    Fixture for case03
    """
    dc_net = DatacenterNetworks()
    dc_net.create_networks_in_dc(
        nets_num=5, dc=dc_net.dc_0, prefix=dc_net.dc_0_prefix
    )
