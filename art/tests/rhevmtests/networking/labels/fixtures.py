#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for labels
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_host
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def add_label_nic_and_network(request):
    """
    Attach label on host NIC and network
    """
    NetworkFixtures()
    labels_list = getattr(request.node.cls, "labels_list")
    labels_dict_to_send = dict()
    for params in labels_list:
        lb = params.get("label")
        host_idx = params.get("host")
        nic_idx = params.get("nic")
        networks = params.get("networks")
        labels_dict_to_send[lb] = {}
        if host_idx is not None:
            labels_dict_to_send[lb]["host"] = conf.HOSTS[host_idx]

        if nic_idx is not None:
            if isinstance(nic_idx, basestring):
                labels_dict_to_send[lb]["nic"] = nic_idx
            else:
                vds_host = conf.VDS_HOSTS[host_idx]
                labels_dict_to_send[lb]["nic"] = vds_host.nics[nic_idx]

        if networks:
            labels_dict_to_send[lb]["networks"] = networks

        testflow.setup("Add label %s: %s", lb, labels_dict_to_send[lb])
        assert ll_networks.add_label(**labels_dict_to_send)
        labels_dict_to_send = dict()


@pytest.fixture(scope="class")
def create_network_on_dc_and_cluster(request):
    """
    Create network on datacenter
    """
    labels = NetworkFixtures()
    datacenter = getattr(request.node.cls, "datacenter", labels.dc_0)
    networks_dict = getattr(request.node.cls, "networks_dict")
    cluster_list = getattr(request.node.cls, "cluster_list", list())
    testflow.setup(
        "Add networks: %s to datacenter %s", ",".join(networks_dict.keys()),
        datacenter
    )
    assert hl_networks.create_and_attach_networks(
        data_center=datacenter, network_dict=networks_dict
    )
    for cluster in cluster_list:
        testflow.setup(
            "Add networks: %s to cluster %s", ",".join(networks_dict.keys()),
            cluster
        )
        assert hl_networks.create_and_attach_networks(
            cluster=cluster, network_dict=networks_dict
        )


@pytest.fixture(scope="class")
def create_datacenter(request):
    """
    Create datacenter
    """
    datacenter = request.node.cls.datacenter

    def fin():
        """
        Remove datacenter
        """
        testflow.teardown("Remove datacenter %s", datacenter)
        assert ll_datacenters.remove_datacenter(
            positive=True, datacenter=datacenter
        )
    request.addfinalizer(fin)

    testflow.setup("Create datacenter %s", datacenter)
    assert ll_datacenters.addDataCenter(
        positive=True, name=datacenter, version=conf.COMP_VERSION_4_0[0],
        local=False
    )


@pytest.fixture(scope="class")
def move_host_to_another_cluster(request):
    """
    Deactivate host and move it to another cluster
    """
    labels = NetworkFixtures()

    def fin():
        """
        Move host back to it's original cluster
        """
        testflow.teardown(
            "Move host %s to cluster %s", labels.host_1_name, labels.cluster_0
        )
        assert hl_host.deactivate_host_if_up(host=labels.host_1_name)
        assert ll_hosts.update_host(
            positive=True, host=labels.host_1_name, cluster=labels.cluster_0
        )
        assert ll_hosts.activate_host(positive=True, host=labels.host_1_name)
    request.addfinalizer(fin)

    testflow.setup("Deactivate host %s", labels.host_1_name)
    assert ll_hosts.deactivate_host(positive=True, host=labels.host_1_name)
