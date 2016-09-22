#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for datacenter networks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as dc_conf
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def datacenter_networks_prepare_setup(request):
    """
    Prepare setup
    """
    NetworkFixtures()
    dc_list = dc_conf.DATACENTER_NETWORKS_DC_NAMES
    result_list = list()

    def fin():
        """
        Remove basic setup
        """
        for dc_name in dc_list:
            result_list.append(
                hl_networks.remove_basic_setup(datacenter=dc_name)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for dc in dc_list:
        assert hl_networks.create_basic_setup(
            datacenter=dc, version=conf.COMP_VERSION
        )


@pytest.fixture(scope="class")
def create_network_in_datacenter(request, datacenter_networks_prepare_setup):
    """
    create network in datacenter
    """
    NetworkFixtures()
    net_name = request.node.cls.net_name
    dc_1 = dc_conf.DATACENTER_NETWORKS_DC_NAMES[1]

    for idx, (key, val) in enumerate(
        dc_conf.DATACENTER_NETWORKS_NET_DICT.iteritems()
    ):
        kwargs_dict = {
            key: val,
            "name": net_name[idx]
        }
        assert ll_networks.create_network_in_datacenter(
            positive=True, datacenter=dc_1, **kwargs_dict
        )


@pytest.fixture(scope="class")
def create_networks_in_dc(request, datacenter_networks_prepare_setup):
    """
    Create networks in datacenter.
    """
    datacenter_networks = NetworkFixtures()
    nets_num_list = request.node.cls.nets_num_list
    dc_list = request.node.cls.dc_list
    prefix_list = request.node.cls.prefix_list

    def fin():
        """
        Remove networks from setup
        """
        for dc_name in dc_list:
            assert ll_networks.delete_networks_in_datacenter(
                datacenter=dc_name, mgmt_net=datacenter_networks.mgmt_bridge
            )
    request.addfinalizer(fin)

    for idx, (nets_num, dc, prefix) in enumerate(
        zip(nets_num_list, dc_list, prefix_list)
    ):
        dc_net_list = ll_networks.create_networks_in_datacenter(
            num_of_net=nets_num, datacenter=dc, prefix=prefix
        )
        if dc_conf.DATACENTER_NETWORKS_DC_NAMES[0] == dc:
            dc_conf.DC_0_NET_LIST = dc_net_list

        if dc_conf.DATACENTER_NETWORKS_DC_NAMES[1] == dc:
            dc_conf.DC_1_NET_LIST = dc_net_list
