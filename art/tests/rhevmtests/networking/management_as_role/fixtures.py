#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for management_as_role
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as conf
import helper
from rhevmtests import networking


class PrepareSetupCase08(object):
    """
    Setup and Teardown for case08
    """
    def __init__(self):
        self.cluster_0 = conf.EXTRA_CL[0]
        self.cluster_1 = conf.EXTRA_CL[1]
        self.cluster_2 = conf.EXTRA_CL[2]
        self.net_1 = conf.NET_1
        self.net_2 = conf.NET_2
        self.dc = conf.EXT_DC_0
        self.cluster_list = [self.cluster_1, self.cluster_2]
        self.cluster_nets_dict = {
            self.cluster_1: [self.net_1, self.net_2],
            self.cluster_2: [self.net_2, self.net_1]
        }
        self.local_dict = {
            self.net_2: {
                "required": "true",
            },
        }

    def move_host_to_new_cluster(self):
        """
        Move host to new cluster
        """
        helper.install_host_new_mgmt()

    def create_and_attach_network(self):
        """
        Create and attach network
        """
        if not hl_networks.createAndAttachNetworkSN(
            data_center=self.dc,  network_dict=self.local_dict
        ):
            raise conf.NET_EXCEPTION()

    def create_clusters_and_attach_networks(self):
        """
        Create clusters and attach networks to the clusters
        """
        for cl in self.cluster_list:
            mgmt_net = self.cluster_nets_dict[cl][0]
            net = self.cluster_nets_dict[cl][1]
            helper.add_cluster(
                cl=cl, dc=self.dc, management_network=mgmt_net
            )
            if not ll_networks.add_network_to_cluster(
                positive=True, network=net, cluster=cl, required=True
            ):
                raise conf.NET_EXCEPTION()

    def move_host_to_original_cluster(self):
        """
        Move host to original cluster
        """
        helper.install_host_new_mgmt(
            network=self.net_1, dest_cl=conf.CL_0, new_setup=False,
            remove_setup=True, maintenance=False
        )

    def remove_clusters(self):
        """
        Remove clusters
        """
        for cl in self.cluster_list:
            ll_clusters.removeCluster(positive=True, cluster=cl)


@pytest.fixture(scope="class")
def prepare_setup_case_08(request):
    """
    Move host to new DC/cluster with net1 as management network
    Create network net2 on DC
    Create 2 clusters
    Attach both networks to each cluster
    Final result should be:
        cluster_0 with host and management network net_1
        cluster_1 without host and management network net_1 and net_2
            attached to the cluster
        cluster_2 without host and management network net_2 and net_1
            attached to the cluster
    """
    ps = PrepareSetupCase08()

    @networking.ignore_exception
    def fin2():
        """
        Finalizer for remove clusters
        """
        ps.remove_clusters()
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Finalizer for move host to original cluster
        """
        ps.move_host_to_original_cluster()
    request.addfinalizer(fin1)

    ps.move_host_to_new_cluster()
    ps.create_and_attach_network()
    ps.create_clusters_and_attach_networks()
