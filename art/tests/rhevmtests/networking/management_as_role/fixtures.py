#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Management Network As A Role test cases
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import helper
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def create_basic_setup(request):
    """
    Create basic setup (Data-Center and optional cluster)
    """
    dc = request.node.cls.ext_dc
    cluster = getattr(request.node.cls, "ext_cluster", None)

    def fin():
        """
        Remove basic setup
        """
        assert hl_networks.remove_basic_setup(datacenter=dc, cluster=cluster)
    request.addfinalizer(fin)

    assert hl_networks.create_basic_setup(
        datacenter=dc, cluster=cluster, version=conf.COMP_VERSION,
        cpu=conf.CPU_NAME
    )


@pytest.fixture(scope="class")
def create_and_attach_network(request):
    """
    Create and attach network to Data-Centers and clusters
    """
    dcs_clusters = request.cls.create_and_attach_network_params[0]
    setup = request.cls.create_and_attach_network_params[1]

    for dc, cl in dcs_clusters:
        assert hl_networks.create_and_attach_networks(
            data_center=dc, cluster=cl, network_dict=setup
        )


@pytest.fixture(scope="class")
def remove_all_networks(request):
    """
    Remove all networks from Data-Center
    """
    dcs = request.cls.remove_all_networks_params

    def fin():
        for dc in dcs:
            assert hl_networks.remove_all_networks(datacenter=dc)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_cluster_network_usages(request):
    """
    Update cluster network usages
    """
    cluster = request.cls.update_cluster_network_usages_params[0]
    net = request.cls.update_cluster_network_usages_params[1]
    usages = request.cls.update_cluster_network_usages_params[2]

    assert ll_networks.update_cluster_network(
        positive=True, cluster=cluster, network=net, usages=usages
    )


@pytest.fixture(scope="class")
def move_host_to_cluster(request):
    """
    Move vds host to a specified cluster
    """
    mgmt_as_role = NetworkFixtures()
    host = mgmt_as_role.hosts_list[request.cls.move_host_to_cluster_params[0]]
    cl = request.cls.move_host_to_cluster_params[1]

    def fin2():
        """
        Activate host after updating its cluster
        """
        assert ll_hosts.activateHost(positive=True, host=host)
    request.addfinalizer(fin2)

    def fin1():
        """
        Move host to a specified cluster
        """
        assert ll_hosts.updateHost(positive=True, host=host, cluster=cl)
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def add_networks_to_clusters(request):
    """
    Add network(s) to cluster(s)
    """
    cl_nets = request.cls.add_networks_to_clusters_params

    for cl, net in cl_nets:
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
            mgmt_net=mgmt_net, network=net, remove_setup=True,
            maintenance=False, new_setup=False
        )
    request.addfinalizer(fin)

    vds_host_obj = mgmt_as_role.vds_list[host_index]

    assert helper.install_host_new_mgmt(
        dc=dc, cl=dst_cl, dest_cl=dst_cl, net_setup=net_setup,
        mgmt_net=mgmt_net, host_resource=vds_host_obj
    )
