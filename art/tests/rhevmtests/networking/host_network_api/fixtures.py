#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_api
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as network_api_conf
import helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def attach_net_to_host(request):
    """
    Attach network to host NIC
    """

    network_api = NetworkFixtures()
    host_nic = None
    hosts_nets_nic_dict = request.node.cls.sn_dict
    for key, val in hosts_nets_nic_dict.iteritems():
        network = val.get("network")
        nic = val.get("nic")
        nic = network_api.host_0_nics[nic] if nic else None
        sn_dict = {
            "network": network
        }
        if nic:
            sn_dict["nic"] = nic
        else:
            host_nic = network_api.host_0_nics[key]

        log = nic if nic else host_nic

        testflow.setup("Attach network %s to host NIC %s", network, log)
        assert hl_host_network.add_network_to_host(
            host_name=conf.HOST_0_NAME, nic_name=host_nic, **sn_dict
        )


@pytest.fixture(scope="class")
def create_network_in_dc_and_cluster(request):
    """
    Create network in datacenter and cluster.
    """
    network_api = NetworkFixtures()
    net = request.node.cls.net

    network_dict = {
        net: {
            "required": "false"
        }
    }
    testflow.setup(
        "Create network %s in datacenter %s and cluster %s",
        net, network_api.dc_0, network_api.cluster_0
    )
    assert hl_networks.createAndAttachNetworkSN(
        data_center=network_api.dc_0, cluster=network_api.cluster_0,
        network_dict=network_dict
    )


@pytest.fixture(scope="class")
def remove_network(request):
    """
    Remove network.
    """
    network_api = NetworkFixtures()
    net = request.node.cls.net
    testflow.setup("Remove network %s", net)
    assert ll_networks.remove_network(
        positive=True, network=net, data_center=network_api.dc_0
    )


@pytest.fixture(scope="class")
def update_host_to_another_cluster(request):
    """
    Update host to another cluster.
    """
    network_api = NetworkFixtures()

    def fin():
        """
        Move host to original cluster.
        """
        testflow.teardown(
            "Move host %s to original cluster %s", network_api.host_0_name,
            network_api.cluster_0
        )
        ll_hosts.updateHost(
            positive=True, host=network_api.host_0_name,
            cluster=network_api.cluster_0
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Update host %s to cluster %s", network_api.host_0_name,
        network_api_conf.SYNC_CL
    )
    assert ll_hosts.updateHost(
        positive=True, host=network_api.host_0_name,
        cluster=network_api_conf.SYNC_CL
    )


@pytest.fixture(scope="class")
def manage_ip_and_refresh_capabilities(request):
    """
    Set temporary IP on interface and refresh capabilities.
    """
    NetworkFixtures()
    for net, actual_ip, actual_netmask, set_ip in (
        request.node.cls.manage_ip_list
    ):
        testflow.setup(
            "Set temporary IP %s on interface %s and refresh capabilities",
            actual_ip, net
        )
        if not actual_netmask:
            actual_netmask = "24"

        helper.manage_ip_and_refresh_capabilities(
            interface=net, ip=actual_ip, netmask=actual_netmask, set_ip=set_ip
        )
