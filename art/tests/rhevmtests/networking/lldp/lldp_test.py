#! /usr/bin/env python
# -*- coding: utf-8 -*-

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as conf
from art.unittest_lib import NetworkTest, tier2
from art.test_handler.tools import polarion, bz


@tier2
@polarion("RHEVM-22039")
@bz(
    {
        "1484725": {},
        "1487078": {},
        "1487157": {},
        "1487930": {}
    }
)
class TestLldp(NetworkTest):
    """
    1. Get LLDP info for host NIC
    """
    def test_lldp_info(self):
        """
        Get LLDP info for host NIC
        """
        assert ll_hosts.get_lldp_nic_info(
            host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[0]
        )
