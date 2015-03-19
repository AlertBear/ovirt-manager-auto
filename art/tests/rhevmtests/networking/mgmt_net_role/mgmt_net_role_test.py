#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing  Management network as a role feature
Several DCs, several clusters with/without the host will be created
"""

import logging
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import helper

import config as c

logger = logging.getLogger("MGMT_Net_Role_Cases")


@attr(tier=1)
class TestMGMTNetRole01(TestCase):
    """
    RHEVM3-6466
    1. Create a new DC and cluster
    2. Check that MGMT of DC and cluster is the default MGMT (ovirtmgmt)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster
        """
        helper.create_setup(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0)

    @polarion("RHEVM3-6466")
    def test_default_mgmt_net(self):
        """
        1. Check that the default MGMT network exists on DC
        2. Check that the default MGMT network exists on cluster
        """
        logger.info(
            "Check network %s exists on DC %s", c.MGMT_BRIDGE, c.EXT_DC_0
        )
        if not ll_networks.get_network_in_datacenter(
            c.MGMT_BRIDGE, c.EXT_DC_0
        ):
            raise c.NET_EXCEPTION(
                "Network %s doesn't exist on DC %s" %
                (c.MGMT_BRIDGE, c.EXT_DC_0)
            )

        logger.info(
            "Check network %s exists on cluster %s", c.MGMT_BRIDGE,
            c.EXTRA_CLUSTER_0
        )
        if not ll_networks.get_dc_network_by_cluster(
            c.EXTRA_CLUSTER_0, c.MGMT_BRIDGE
        ):
            raise c.NET_EXCEPTION(
                "Network %s doesn't exist on cluster %s" %
                (c.MGMT_BRIDGE, c.EXTRA_CLUSTER_0)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and cluster
        """
        helper.remove_dc_cluster()


@attr(tier=1)
class TestMGMTNetRole02(TestCase):
    """
    RHEVM3-6474 - Updating MGMT network
    1. Negative: Try to update default MGMT to network that is non-required
    2. Update default MGMT to network that is required

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new cluster
        2. Create required network
        3. Create non-required network
        """

        helper.add_cluster()
        local_dict = {
            c.net1: {"required": "true"},
            c.net2: {"required": "false"}
        }
        helper.create_net_dc_cluster(
            dc=c.ORIG_DC, cl=c.EXTRA_CLUSTER_0, net_dict=local_dict
        )

    @polarion("RHEVM3-6474")
    def test_req_nonreq_mgmt_net(self):
        """
        1. Update MGMT network to be required network sw1
        2. Check that MGMT network is sw1
        3. Try to update MGMT network to be non-required network sw2
        4. Check that MGMT network is still sw1
        """
        helper.update_mgmt_net()
        helper.check_mgmt_net()

        helper.update_mgmt_net(net=c.net2, positive=False)
        logger.info(
            "Check MGMT network on cluster %s is still %s ",
            c.EXTRA_CLUSTER_0, c.net1
        )
        helper.check_mgmt_net()

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove required and non-required networks
        """
        helper.remove_cl()

        logger.info("Remove all networks besides MGMT")
        if not hl_networks.remove_all_networks(
            datacenter=c.ORIG_DC, mgmt_network=c.MGMT_BRIDGE
        ):
            logger.error("Cannot remove networks from setup")
