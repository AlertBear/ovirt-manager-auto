#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OVN cluster tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.clusters as hl_clusters
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import config as ovn_conf
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, tier2
from fixtures import get_default_ovn_provider
from rhevmtests.fixtures import create_clusters


@pytest.mark.incremental
@pytest.mark.usefixtures(
    get_default_ovn_provider.__name__,
    create_clusters.__name__
)
class TestOVNCluster(NetworkTest):
    """
    Add cluster of type OVN to Data-Center
    """
    # Common settings
    provider_name = ovn_conf.OVN_PROVIDER_NAME
    ovn_cluster = "ovn_cluster_test"

    # create_clusters fixture params
    clusters_to_remove = [ovn_cluster]

    @tier2
    @polarion("RHEVM-24506")
    def test_add_ovn_cluster(self):
        """
        Add cluster with OVN provider: 'ovirt-provider-ovn'
        """
        assert ll_clusters.addCluster(
            positive=True, name=self.ovn_cluster,
            cpu=net_conf.CPU_NAME, data_center=net_conf.DC_0,
            external_network_provider=ovn_conf.OVN_PROVIDER_NAME
        )

    @tier2
    @polarion("RHEVM-25040")
    def test_cluster_type(self):
        """
        Check cluster external network provider name
        """
        names = hl_clusters.get_external_network_provider_names(
            cluster_name=self.ovn_cluster
        )
        assert names and len(names) == 1
        assert names[0] == self.provider_name

    @tier2
    @polarion("RHEVM-24679")
    def test_delete_ovn_cluster(self):
        """
        Remove cluster with OVN provider: 'ovirt-provider-ovn'
        """
        assert ll_clusters.removeCluster(
            positive=True, cluster=self.ovn_cluster
        )
        self.clusters_to_remove.remove(self.ovn_cluster)
