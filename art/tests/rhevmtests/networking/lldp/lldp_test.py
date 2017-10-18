#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as conf
from art.unittest_lib import NetworkTest, tier2
from art.core_api import apis_utils
from art.test_handler.tools import polarion, bz
from art.core_api import apis_exceptions
from rhevmtests.networking.fixtures import (  # noqa: F401
    remove_all_networks,
    setup_networks_fixture,
    clean_host_interfaces,
    create_and_attach_networks,

)


@tier2
@polarion("RHEVM-22039")
@bz({"1494921": {}})
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestLldp(NetworkTest):
    """
    1. Get LLDP info for host NIC
    """
    # General params
    lldp_net = "lldp-vlan-1-net"

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
            "networks": {
                lldp_net: {
                    "vlan_id": "1",
                    "required": "false"
                }
            }
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [conf.DC_0]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            lldp_net: {
                "network": lldp_net,
                "nic": 0
            }
        }
    }
    # clean_host_interfaces params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    def test_lldp_info(self):
        """
        Get LLDP info for host NIC
        """
        nic = conf.HOST_0_NICS[0]
        host_obj = ll_hosts.get_host_object(host_name=conf.HOST_0_NAME)
        sampler = apis_utils.TimeoutingSampler(
            timeout=60,
            sleep=1,
            func=ll_hosts.get_lldp_nic_info,
            host=host_obj,
            nic=nic
        )
        for sample in sampler:
            try:
                if not sample:
                    continue
                break
            except apis_exceptions.APITimeout:
                assert sample, "Failed to get LLDP info for %s" % nic
