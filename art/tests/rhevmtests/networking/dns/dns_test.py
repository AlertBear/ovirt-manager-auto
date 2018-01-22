#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
DNS tests
"""

import pytest

import helper
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
)
from rhevmtests import helpers
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as dns_conf
from rhevmtests.networking import (
    config as conf,
)
from art.test_handler.tools import polarion, bz
from art.core_api import apis_utils
from art.unittest_lib import NetworkTest, testflow, tier2
from fixtures import (  # noqa: F401
    get_hosts_params,
    restore_host_dns_servers
)


@pytest.mark.usefixtures(restore_host_dns_servers.__name__)
class TestDns01(NetworkTest):
    """
    1. Edit and update the default route network with new DNS configuration
    2. Edit and update the default route network with 2 new DNS configurations
    3. Edit the default route network and remove 1 name server
    """

    network = conf.MGMT_BRIDGE
    dc = conf.DC_0

    # parametrize params
    # [DNS_SERVERS, UPDATE VIA]

    # Update via network
    update_dns_network = [dns_conf.DNS_1, "network"]
    add_dns_network = [dns_conf.DNS_1 + dns_conf.DNS_2, "network"]
    remove_dns_network = [dns_conf.DNS_2, "network"]

    # Update via network attachment
    update_dns_attachment = [dns_conf.DNS_1, "attachment"]
    add_dns_attachment = [dns_conf.DNS_1 + dns_conf.DNS_2, "attachment"]
    remove_dns_attachment = [dns_conf.DNS_2, "attachment"]

    @tier2
    @pytest.mark.parametrize(
        ("dns", "via"),
        [
            # via network
            pytest.param(
                *update_dns_network, marks=(polarion("RHEVM3-16939"))
            ),
            pytest.param(
                *add_dns_network, marks=(polarion("RHEVM3-16940"))
            ),
            pytest.param(
                *remove_dns_network, marks=(
                    (polarion("RHEVM3-17095"), bz({"1537095": {}}))
                )
            ),

            # via network attachment
            pytest.param(
                *update_dns_attachment, marks=(polarion("RHEVM3-16942"))
            ),
            pytest.param(
                *add_dns_attachment, marks=(polarion("RHEVM3-16946"))
            ),
            pytest.param(
                *remove_dns_attachment, marks=(polarion("RHEVM3-17096"))
            ),
        ],
        ids=[
            # via network
            "Edit_DNS_via_network",
            "Add_DNS_via_network",
            "Remove_DNS_via_network",

            # via network attachment
            "Edit_DNS_via_network_attachment",
            "Add_DNS_via_network_attachment",
            "Remove_DNS_via_network_attachment",
        ]
    )
    def test_set_dns_via_network(self, dns, via):
        """
        Update/add/delete DNS servers
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_set_dns_via_network.parametrize,
            params=[dns, via]
        )
        testflow.step(_id)
        host = dns_conf.WORKING_HOST

        if via == "network":
            assert ll_networks.update_network(
                positive=True, network=self.network, data_center=self.dc,
                dns=dns
            )

        if via == "attachment":
            sn_dict = {
                "update": {
                    "1": {
                        "datacenter": self.dc,
                        "network": self.network,
                        "dns": dns
                    }
                }
            }
            assert hl_host_network.setup_networks(
                host_name=host, retry=True, **sn_dict
            )

        sample = apis_utils.TimeoutingSampler(
            timeout=300, sleep=1,
            func=lambda: helper.get_host_dns_servers(host=host) == dns

        )
        assert sample.waitForFuncStatus(result=True)
