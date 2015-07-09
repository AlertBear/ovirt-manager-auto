#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network test cases that do not fit to any feature plan
"""

import logging
from rhevmtests.networking import config
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Misc_Cases")

DC_0 = config.DC_NAME[0]


@attr(tier=1)
class TestMisc01(TestCase):
    """
    1. Create new network called 'net-155'
    2. Create new network called 'net-1-5-5-b----'
    3. Create new network called 'm-b_1-2_3_4-3_5'
    """

    __test__ = True

    @polarion("RHEVM3-11877")
    def test_create_net_with_dash(self):
        """
        1. Create new network called 'net-155'
        2. Create new network called 'net-1-5-5-b----'
        3. Create new network called 'm-b_1-2_3_4-3_5'
        """
        networks = ["net-155", "net-1-5-5-b----", "m-b_1-2_3_4-3_5"]
        for net in networks:
            logger.info("Create %s on %s", net, DC_0)
            if not ll_networks.addNetwork(
                positive=True, name=net, data_center=DC_0
            ):
                raise config.NET_EXCEPTION(
                    "Failed to create %s on %s" % (net, DC_0)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the DC
        """
        logger.info("Removing all networks from %s", DC_0)
        if not hl_networks.remove_all_networks(
            datacenter=DC_0, mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Failed to remove all networks from %s", DC_0)
