#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing DataCenter Networks feature.
https://bugzilla.redhat.com/show_bug.cgi?id=741111
2 DC will be created for testing.
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import fixture_case_01, fixture_case_02, fixture_case_03

logger = logging.getLogger("DC_Networks_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_01.__name__)
class TestDataCenterNetworksCase1(NetworkTest):
    """
    List all networks under datacenter.
    """
    __test__ = True

    @polarion("RHEVM3-4132")
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        testflow.step("Checking that all networks exist in the datacenters")
        engine_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.DATACENTER_NETWORKS_DC_NAMES[0]
        )
        for net in conf.DC_0_NET_LIST:
            self.assertIn(
                net, [i.name for i in engine_dc_net_list],
                "%s was expected to be in %s" %
                (net, conf.DATACENTER_NETWORKS_DC_NAMES[0])
            )
        engine_extra_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.DATACENTER_NETWORKS_DC_NAMES[1]
        )
        for net in conf.DC_1_NET_LIST:
            self.assertIn(
                net, [i.name for i in engine_extra_dc_net_list],
                "%s was expected to be in %s" %
                (net, conf.DATACENTER_NETWORKS_DC_NAMES[1])
            )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_02.__name__)
class TestDataCenterNetworksCase2(NetworkTest):
    """
    Create network under datacenter.
    """
    __test__ = True

    @polarion("RHEVM3-4135")
    def test_verify_network_parameters(self):
        """
        Verify that all networks have the correct parameters.
        """
        testflow.step("Verify that all networks have the correct parameters")
        for key, val in conf.DATACENTER_NETWORKS_NET_DICT.iteritems():
            name = "_".join([ll_networks.NETWORK_NAME, key])
            net_obj = ll_networks.get_network_in_datacenter(
                name, conf.DATACENTER_NETWORKS_DC_NAMES[1]
            )

            if key == "vlan_id":
                res = net_obj.get_vlan().get_id()

            elif key == "usages":
                res = net_obj.get_usages().get_usage()

            else:
                res = getattr(net_obj, key)

            self.assertEqual(
                res, val, "%s %s should be %s but have %s" %
                          (name, key, val, res)
            )

    @polarion("RHEVM3-4134")
    def test_delete_networks(self):
        """
        Delete networks under datacenter.
        """
        testflow.step("Delete all networks from datacenter")
        self.assertTrue(
            ll_networks.delete_networks_in_datacenter(
                datacenter=conf.DC_0, mgmt_net=conf.MGMT_BRIDGE
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_case_03.__name__)
class TestDataCenterNetworksCase3(NetworkTest):
    """
    Update network under datacenter.
    """
    __test__ = True

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
        testflow.step(
            "Update networks under %s", conf.DATACENTER_NETWORKS_DC_NAMES[0]
        )
        for idx, net in enumerate(conf.DC_0_NET_LIST):
            key = conf.DATACENTER_NETWORKS_VERIFY_NET_LIST[idx]
            val = conf.DATACENTER_NETWORKS_NET_DICT[
                conf.DATACENTER_NETWORKS_VERIFY_NET_LIST[idx]
            ]
            kwargs_dict = {key: val}
            self.assertTrue(
                ll_networks.update_network_in_datacenter(
                    positive=True, network=net,
                    datacenter=conf.DATACENTER_NETWORKS_DC_NAMES[0],
                    **kwargs_dict
                )
            )
