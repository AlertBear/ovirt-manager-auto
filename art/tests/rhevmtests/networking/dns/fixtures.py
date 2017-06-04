#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures for DNS tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as dns_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module", autouse=True)
def get_host_dns_servers(request):
    """
    Get host DNS servers and store them in config
    """
    NetworkFixtures()
    dns_servers = helper.get_host_dns_servers()
    assert dns_servers
    dns_conf.HOST_DNS_SERVERS = dns_servers


@pytest.fixture(scope="class")
def restore_host_dns_servers(request):
    """
    Restore host DNS servers
    """
    results = list()
    network = conf.MGMT_BRIDGE
    dns = dns_conf.HOST_DNS_SERVERS
    dc = conf.DC_0
    sn_dict = {
        "update": {
            "1": {
                "datacenter": dc,
                "network": network,
                "dns": list()
            }
        }
    }

    def fin4():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin4)

    def fin3():
        """
        Remove DNS checkbox from the network
        """
        results.append(
            (
                ll_networks.update_network(
                    positive=True, network=network, dns=list(), data_center=dc
                ), "fin3: ll_networks.update_network (remove DNS checkbox)"
            )
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Restore host DNS servers
        """
        results.append(
            (
                hl_host_network.setup_networks(
                    host_name=conf.HOST_2_NAME, **sn_dict
                ), "fin2: hl_host_network.setup_networks"
            )
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Restore network DNS servers
        """
        results.append(
            (
                ll_networks.update_network(
                    positive=True, network=network, dns=dns, data_center=dc
                ), "fin1: ll_networks.update_network"
            )
        )
    request.addfinalizer(fin1)
