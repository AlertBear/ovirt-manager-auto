#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for datacenter networks
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as dc_conf
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def create_network_in_datacenter(request):
    """
    create network in datacenter
    """
    net_name = request.node.cls.net_name
    dc_1 = dc_conf.DATACENTER_NETWORKS_DC_NAMES[1]

    for idx, (key, val) in enumerate(
        dc_conf.DATACENTER_NETWORKS_NET_DICT.iteritems()
    ):
        kwargs_dict = {
            key: val,
            "name": net_name[idx]
        }
        testflow.setup(
            "Add network to datatcenter %s with %s", dc_1, kwargs_dict
        )
        assert ll_networks.create_network_in_datacenter(
            positive=True, datacenter=dc_1, **kwargs_dict
        )


@pytest.fixture(scope="class")
def create_networks_in_dc(request):
    """
    Create networks in datacenter.
    """
    nets_num_list = request.node.cls.nets_num_list
    dc_list = request.node.cls.dc_list
    prefix_list = request.node.cls.prefix_list

    def fin():
        """
        Remove networks from setup
        """
        for dc_name in dc_list:
            testflow.teardown("Remove network from setup")
            assert ll_networks.delete_networks_in_datacenter(
                datacenter=dc_name, mgmt_net=conf.MGMT_BRIDGE
            )
    request.addfinalizer(fin)

    for idx, (nets_num, dc, prefix) in enumerate(
        zip(nets_num_list, dc_list, prefix_list)
    ):
        testflow.setup("Create networks in datacenter %s", dc)
        dc_net_list = ll_networks.create_networks_in_datacenter(
            num_of_net=nets_num, datacenter=dc, prefix=prefix
        )
        if dc_conf.DATACENTER_NETWORKS_DC_NAMES[0] == dc:
            dc_conf.DC_0_NET_LIST = dc_net_list

        if dc_conf.DATACENTER_NETWORKS_DC_NAMES[1] == dc:
            dc_conf.DC_1_NET_LIST = dc_net_list
