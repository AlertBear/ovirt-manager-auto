#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing DataCenter Networks feature
https://bugzilla.redhat.com/show_bug.cgi?id=741111
5 DC's will be created for testing
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as dc_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, tier2
from fixtures import create_networks_on_dc
from rhevmtests.fixtures import create_datacenters


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_networks_on_dc.__name__
)
class TestDataCenterNetworks(NetworkTest):
    """
    1. Get Data-Center network list
    2. Verify that all networks were created with correct network properties
    3. Delete all networks from Data-Center
    4. Update Data-Center network properties
    """
    # create_datacenters fixture params
    datacenters_dict = dc_conf.DC_CONFIG

    # create_networks_on_dc fixture params
    create_networks_on_dc_params = dc_conf.CREATE_NETWORKS

    @tier2
    @polarion("RHEVM3-4132")
    def test_get_network_list(self):
        """
        Get Data-Center network list
        """
        for dc in dc_conf.DCS_CASE_1:
            created_nets = dc_conf.NETS_CASE_1
            # By default, ovirtmgmt network is already exists on DC
            created_nets.append("ovirtmgmt")
            testflow.step("Getting a list of all networks in DC: %s", dc)
            net_list = ll_networks.get_networks_in_datacenter(datacenter=dc)
            non_created_nets = [
                net.name for net in net_list if net.name not in created_nets
            ]
            assert not non_created_nets, (
                "Unexpected networks: %s exists on DC: %s"
                % (non_created_nets, dc)
            )

    @tier2
    @polarion("RHEVM3-4135")
    def test_created_network_properties(self):
        """
        Verify that all networks were created with correct network properties
        """
        dc = dc_conf.DCS_CASE_2
        for net in dc_conf.NETS_CASE_2:
            network_obj = ll_networks.get_network_in_datacenter(
                network=net, datacenter=dc
            )
            assert network_obj, "Network: %s not found in DC: %s" % (net, dc)

            net_prop = self.create_networks_on_dc_params.get(dc).get(net)
            net_prop_name, net_prop_value = net_prop.items()[0]

            if net_prop_name == "vlan_id":
                actual_prop_value = network_obj.get_vlan().get_id()
            elif net_prop_name == "usages":
                actual_prop_value = network_obj.usages.get_usage()
            else:
                actual_prop_value = getattr(network_obj, net_prop_name)

            testflow.step(
                "Verifying Data-Center: %s network: %s properties", dc, net
            )
            assert actual_prop_value == net_prop_value, (
                "Network: %s property: %s current value: %s "
                "expected value: %s" % (
                    net, net_prop_name, actual_prop_value,
                    net_prop_value
                )
            )

    @tier2
    @polarion("RHEVM3-4134")
    def test_delete_networks_from_dc(self):
        """
        Delete all networks from Data-Center
        """
        testflow.step(
            "Delete all networks from Data-Center: %s", dc_conf.DCS_CASE_3
        )
        assert ll_networks.delete_networks_in_datacenter(
            datacenter=dc_conf.DCS_CASE_3, mgmt_net=conf.MGMT_BRIDGE
        )

    @tier2
    @polarion("RHEVM3-4133")
    def test_update_dc_networks(self):
        """
        Update Data-Center network properties
        """
        dc = dc_conf.DCS_CASE_4
        for net in dc_conf.NETS_CASE_4:
            for prop_name in dc_conf.CUSTOM_NET_PROPERTIES.keys():
                testflow.step(
                    "Updating Data-Center: %s network: %s properties", dc, net
                )
                assert ll_networks.update_network_in_datacenter(
                    positive=True, network=net, datacenter=dc,
                    **{prop_name: dc_conf.CUSTOM_NET_PROPERTIES[prop_name]}
                )
