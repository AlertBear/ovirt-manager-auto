#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing DataCenter Networks feature.
https://bugzilla.redhat.com/show_bug.cgi?id=741111
2 DC will be created for testing.
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as dc_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import create_networks_in_dc, create_network_in_datacenter
from rhevmtests.fixtures import create_datacenters


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_networks_in_dc.__name__
)
@tier2
class TestDataCenterNetworksCase1(NetworkTest):
    """
    List all networks under datacenter.
    """

    # create_networks_in_dc params
    nets_num_list = [10, 5]
    dc_list = dc_conf.DATACENTER_NETWORKS_DC_NAMES
    prefix_list = ["C1_dcNetwork", "C1_dcNetwork"]

    # create_datacenters params
    datacenters_dict = {
        dc_list[0]: {
            "name": dc_list[0],
            "version": conf.COMP_VERSION,
        },
        dc_list[1]: {
            "name": dc_list[1],
            "version": conf.COMP_VERSION,
        },
    }

    @polarion("RHEVM3-4132")
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        for dc, net_list in (
            (self.dc_list[0], dc_conf.DC_0_NET_LIST),
            (self.dc_list[1], dc_conf.DC_1_NET_LIST)
        ):
            dc_net_list = ll_networks.get_networks_in_datacenter(datacenter=dc)
            testflow.step(
                "Checking that all networks %s exist in the datacenters %s",
                net_list, dc
            )
            assert all(
                map(lambda v: v in [x.name for x in dc_net_list], net_list)
            ), (
                "Not all networks exist in the datacenter %s" % dc
            )


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_network_in_datacenter.__name__
)
@tier2
class TestDataCenterNetworksCase2(NetworkTest):
    """
    Create network under datacenter.
    """
    # create_network_in_datacenter params
    dc_list = dc_conf.DATACENTER_NETWORKS_DC_NAMES
    dc_1 = dc_list[1]
    net_name = dc_conf.NETS[2]

    # create_datacenters params
    datacenters_dict = {
        dc_list[0]: {
            "name": dc_list[0],
            "version": conf.COMP_VERSION,
        },
        dc_list[1]: {
            "name": dc_list[1],
            "version": conf.COMP_VERSION,
        },
    }

    @polarion("RHEVM3-4135")
    def test_01_verify_network_parameters(self):
        """
        Verify that all networks have the correct parameters.
        """
        for idx, (key, val) in enumerate(
            dc_conf.DATACENTER_NETWORKS_NET_DICT.iteritems()
        ):
            testflow.step(
                "Verify that network %s have the correct parameter %s",
                self.net_name[idx], key
            )
            net_obj = ll_networks.get_network_in_datacenter(
                self.net_name[idx], self.dc_1
            )

            if key == "vlan_id":
                res = net_obj.get_vlan().get_id()

            elif key == "usages":
                res = net_obj.get_usages().get_usage()

            else:
                res = getattr(net_obj, key)

            assert res == val, (
                "%s %s should be %s but have %s" % (
                    self.net_name[idx], key, val, res
                )
            )

    @polarion("RHEVM3-4134")
    def test_02_delete_networks(self):
        """
        Delete networks under datacenter.
        """
        testflow.step(
            "Delete all networks %s from datacenter %s", self.net_name,
            self.dc_1
        )
        assert ll_networks.delete_networks_in_datacenter(
            datacenter=self.dc_1, mgmt_net=conf.MGMT_BRIDGE
        )


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_networks_in_dc.__name__
)
@tier2
class TestDataCenterNetworksCase3(NetworkTest):
    """
    Update network under datacenter.
    """
    # create_networks_in_dc
    nets_num_list = [5]
    dc_list = dc_conf.DATACENTER_NETWORKS_DC_NAMES
    dc_1 = dc_list[1]
    prefix_list = ["C3_dcNetwork"]

    # create_datacenters params
    datacenters_dict = {
        dc_list[0]: {
            "name": dc_list[0],
            "version": conf.COMP_VERSION,
        },
        dc_list[1]: {
            "name": dc_list[1],
            "version": conf.COMP_VERSION,
        },
    }

    @polarion("RHEVM3-4133")
    def test_update_networks_parameters(self):
        """
        Update network under datacenter with:
        description
        stp
        vlan_id
        usages
        mtu
        """
        for idx, net in enumerate(dc_conf.DC_0_NET_LIST):
            testflow.step(
                "Update network %s under %s", net, self.dc_list[0]
            )
            key = dc_conf.DATACENTER_NETWORKS_VERIFY_NET_LIST[idx]
            val = dc_conf.DATACENTER_NETWORKS_NET_DICT[key]
            kwargs_dict = {key: val}
            assert ll_networks.update_network_in_datacenter(
                positive=True, network=net, datacenter=self.dc_list[0],
                **kwargs_dict
            )
