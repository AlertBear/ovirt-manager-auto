#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network test cases that do not fit to any feature plan
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import case_01_fixture

logger = logging.getLogger("Misc_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(case_01_fixture.__name__)
class TestMisc01(NetworkTest):
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
            testflow.step("Create %s on %s", net, conf.DC_0)
            assert ll_networks.add_network(
                positive=True, name=net, data_center=conf.DC_0
            )
