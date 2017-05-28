#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Management Network As A Role test cases
"""

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def move_host_to_cluster(request):
    """
    Move host to a specified cluster
    """
    mgmt_as_role = NetworkFixtures()
    host = mgmt_as_role.hosts_list[request.cls.move_host_to_cluster_params[0]]
    vds = mgmt_as_role.vds_list[request.cls.move_host_to_cluster_params[0]]
    cl = request.cls.move_host_to_cluster_params[1]

    def fin3():
        """
        Activate host after updating its cluster
        """
        assert ll_hosts.activate_host(positive=True, host=host)
    request.addfinalizer(fin3)

    def fin2():
        """
        Move host to a specified cluster
        """
        assert ll_hosts.update_host(positive=True, host=host, cluster=cl)
    request.addfinalizer(fin2)

    def fin1():
        """
        Deactivate host if up
        """
        assert hl_hosts.deactivate_host_if_up(host=host, host_resource=vds)
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def add_networks_to_clusters(request):
    """
    Add network(s) to cluster(s)
    """
    cl_nets = request.cls.add_networks_to_clusters_params

    for cl, net in cl_nets:
        testflow.setup("Add network %s to cluster %s", net, cl)
        assert ll_networks.add_network_to_cluster(
            positive=True, network=net, cluster=cl, required=True
        )


@pytest.fixture(scope="class")
def remove_network(request):
    """
    Remove a network from Data-Center
    """
    dc = request.cls.remove_network_params[0]
    net = request.cls.remove_network_params[1]

    testflow.setup("Remove network %s from datacenter %s", net, dc)
    assert ll_networks.remove_network(
        positive=True, network=net, data_center=dc
    )


@pytest.fixture(scope="class")
def install_host_with_new_management(request):
    """
    Install host with new management network
    """
    mgmt_as_role = NetworkFixtures()

    host_index = request.cls.install_host_with_new_management_params[0]
    net = request.cls.install_host_with_new_management_params[1]
    src_cl = request.cls.install_host_with_new_management_params[2]
    dst_cl = request.cls.install_host_with_new_management_params[3]
    dc = request.cls.install_host_with_new_management_params[4]
    net_setup = request.cls.install_host_with_new_management_params[5]
    mgmt_net = request.cls.install_host_with_new_management_params[6]

    def fin():
        """
        Reinstall host on origin cluster
        """
        assert helper.install_host_new_mgmt(
            dc=dc, cl=dst_cl, dest_cl=src_cl, net_setup=net_setup,
            mgmt_net=mgmt_net, network=net, remove_setup=True, new_setup=False
        )
    request.addfinalizer(fin)

    vds_host_obj = mgmt_as_role.vds_list[host_index]

    testflow.setup("Install host with new management network %s", mgmt_net)
    assert helper.install_host_new_mgmt(
        dc=dc, cl=dst_cl, dest_cl=dst_cl, net_setup=net_setup,
        mgmt_net=mgmt_net, host_resource=vds_host_obj
    )
