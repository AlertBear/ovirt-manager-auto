#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test cases for Management Network As A Role feature

The following elements will be used for the testing:

Data-Centers (default and extra), clusters, host, networks
(both management and non-management)
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as mgmt_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    create_basic_setup, remove_all_networks, add_clusters_to_dcs,
    create_and_attach_network, add_networks_to_clusters,
    update_cluster_network_usages, move_host_to_cluster, remove_clusters,
    remove_network, install_host_with_new_management
)


@attr(tier=2)
@pytest.mark.usefixtures(
    create_basic_setup.__name__
)
class TestMGMTNetRole01(NetworkTest):
    """
    1.  Create DC and cluster
    2.  Check that the management of the DC and cluster is the default
            management network (ovirtmgmt)
    """
    __test__ = True

    dc = mgmt_conf.DATA_CENTERS[1][0]
    cluster = mgmt_conf.CLUSTERS[1][0]
    create_basic_setup_params = [dc, cluster]

    @polarion("RHEVM3-6466")
    def test_01_default_mgmt_net(self):
        """
        1.  Check that the default management network exists on DC
        2.  Check that the default management network exists on cluster
        """
        testflow.step('Check that the default management network exists on DC')
        management_network_obj = ll_networks.get_management_network(
            cluster_name=self.cluster
        )
        assert management_network_obj

        testflow.step(
            'Check that the default management network exists on cluster'
        )
        assert ll_networks.get_network_in_datacenter(
            network=management_network_obj.name, datacenter=self.dc
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    remove_all_networks.__name__,
    add_clusters_to_dcs.__name__,
    create_and_attach_network.__name__
)
class TestMGMTNetRole02(NetworkTest):
    """
    1.  Try to update default management to network that is non-required
    2.  Update default management to network that is required
    """
    __test__ = True

    dc = conf.DC_0
    cluster = mgmt_conf.CLUSTERS[2][0]
    net_1 = mgmt_conf.NETS[2][0]
    net_2 = mgmt_conf.NETS[2][1]
    net_dict = mgmt_conf.NET_DICT_CASE_02
    create_and_attach_network_params = [[(dc, cluster)], net_dict]
    add_clusters_to_dcs_params = [(cluster, dc, None)]
    remove_all_networks_params = [dc]

    @polarion("RHEVM3-6474")
    def test_01_req_non_req_mgmt_net(self):
        """
        1.  Update management network to be required network net1
        2.  Check that management network is net1
        3.  Try to update management network to be non-required network net2
        4.  Check that management network is still net1
        """
        testflow.step('Update management network to be required network net1')
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster, network=self.net_1,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is net1')
        assert hl_networks.is_management_network(
            network=self.net_1, cluster_name=self.cluster
        )

        testflow.step(
            'Try to update management network to be non-required network net2'
        )
        assert ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is still net1')
        assert hl_networks.is_management_network(
            network=self.net_1, cluster_name=self.cluster
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_basic_setup.__name__,
    add_clusters_to_dcs.__name__,
    create_and_attach_network.__name__
)
class TestMGMTNetRole03(NetworkTest):
    """
    1.  Try to remove default management network when it is attached to cluster
    2.  Remove default management network when it is detached from all clusters
            in the DC
    """
    __test__ = True

    ext_cluster_0 = mgmt_conf.CLUSTERS[3][0]
    ext_cluster_1 = mgmt_conf.CLUSTERS[3][1]
    ext_dc = mgmt_conf.DATA_CENTERS[3][0]
    net_1 = mgmt_conf.NETS[3][0]
    create_and_attach_network_params = [
        [(ext_dc, ext_cluster_0), (None, ext_cluster_1)],
        mgmt_conf.NET_DICT_CASE_03
    ]
    add_clusters_to_dcs_params = [(ext_cluster_1, ext_dc, None)]
    create_basic_setup_params = [ext_dc, ext_cluster_0]

    @polarion("RHEVM3-6476")
    def test_01_remove_mgmt_net(self):
        """
        1.  Update the first cluster to have net1 as its management
        2.  Check that management network is net1 for that cluster
        3.  Negative: try to remove the default management network and fail
        4.  Update the second cluster to have net1 as its management
        5.  Check that management network is net1 for that cluster
        6.  Remove the default management network
        7.  Negative: try to remove net1 and fail
        """
        testflow.step(
            'Update the first cluster to have net1 as its management'
        )

        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.ext_cluster_0, network=self.net_1,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is net1 for that cluster')
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cluster_0, network=self.net_1
        )

        testflow.step(
            'Negative: try to remove the default management network and fail'
        )
        assert ll_networks.remove_network(
            positive=False, network=conf.MGMT_BRIDGE,
            data_center=self.ext_dc
        )

        testflow.step(
            'Update the second cluster to have net1 as its management'
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.ext_cluster_1, network=self.net_1,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is net1 for that cluster')
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cluster_1, network=self.net_1
        )

        testflow.step('Remove the default management network')
        assert ll_networks.remove_network(
            positive=True, network=conf.MGMT_BRIDGE, data_center=self.ext_dc
        )

        testflow.step('Negative: try to remove net1 and fail')
        assert ll_networks.remove_network(
            positive=False, network=self.net_1, data_center=self.ext_dc
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    remove_all_networks.__name__,
    add_clusters_to_dcs.__name__,
    create_and_attach_network.__name__,
    update_cluster_network_usages.__name__
)
class TestMGMTNetRole04(NetworkTest):
    """
    1.  Display and/or migration network fallback
    2.  Management network becomes display network when original display
            network is removed
    3.  Management network becomes migration network when original migration
            network is removed
    """
    __test__ = True

    net_1 = mgmt_conf.NETS[4][0]
    net_2 = mgmt_conf.NETS[4][1]
    net_3 = mgmt_conf.NETS[4][2]
    dc = conf.DC_0
    ext_cls_0 = mgmt_conf.DATA_CENTERS[4][0]
    net_dict = mgmt_conf.NET_DICT_CASE_04
    update_cluster_network_usages_params = [
        ext_cls_0, net_1, conf.MANAGEMENT_NET_USAGE
    ]
    create_and_attach_network_params = [[(dc, ext_cls_0)], net_dict]
    add_clusters_to_dcs_params = [(ext_cls_0, dc, None)]
    remove_all_networks_params = [dc]
    usages_to_check = [conf.DISPLAY_NET_USAGE, conf.MIGRATION_NET_USAGE]

    @polarion("RHEVM3-6469")
    def test_01_display_migration_fallback(self):
        """
        1.  Remove net2 from setup
        2.  Check that net1 is display network
        3.  Remove net3 network
        4.  Check that net1 is migration network
        """
        for net in [self.net_2, self.net_3]:
            testflow.step('Removing network: %s from setup' % net)
            assert ll_networks.remove_network(
                positive=True, network=net, data_center=self.dc
            )

        testflow.step('Checking network usages')
        assert ll_networks.check_network_usage(
            self.ext_cls_0, self.net_1, *self.usages_to_check
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_and_attach_network.__name__,
    remove_all_networks.__name__,
    add_clusters_to_dcs.__name__,
    move_host_to_cluster.__name__
)
class TestMGMTNetRole05(NetworkTest):
    """
    1.  Move the host between clusters with the same management network
    2.  Negative: try to move host between clusters with different management
        networks
    """
    __test__ = True

    dc = conf.DC_0
    ext_cls_0 = mgmt_conf.CLUSTERS[5][0]
    net_1 = mgmt_conf.NETS[5][0]
    net_dict = mgmt_conf.NET_DICT_CASE_05
    move_host_to_cluster_params = [1, conf.CL_0]
    add_clusters_to_dcs_params = [(ext_cls_0, dc, net_1)]
    remove_all_networks_params = [dc]
    create_and_attach_network_params = [[(dc, None)], net_dict]

    @polarion("RHEVM3-6471")
    def test_01_moving_host(self):
        """
        1.  Move the host to another cluster with the default management
            network
        2.  Negative: try to move the host to the cluster with non-default
            management network
        """
        testflow.step(
            'Move the host to another cluster with the default management'
            ' network'
        )
        assert ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME)
        assert helper.move_host_new_cl(host=conf.HOST_1_NAME, cl=conf.CL_1)
        assert ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME)
        assert ll_hosts.deactivateHost(
            positive=True, host=conf.HOST_1_NAME
        )

        testflow.step(
            'Negative: try to move the host to the cluster with non-default'
            ' management network'
        )
        assert helper.move_host_new_cl(
            host=conf.HOST_1_NAME, cl=self.ext_cls_0, positive=False
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_basic_setup.__name__,
    create_and_attach_network.__name__,
    add_clusters_to_dcs.__name__,
    remove_clusters.__name__
)
class TestMGMTNetRole06(NetworkTest):
    """
    1.  Create a new DC and 3 clusters with default, net1 and net2 management
        networks respectively
    2.  Create a new cluster on that DC without explicitly providing management
        and make sure default management was picked up for this cluster
    3.  Remove clusters with default management networks and remove default
        management network
    4.  Try to create a new cluster without providing management network
        explicitly and fail
    5.  Create a new cluster when providing net1 as management network
    """
    __test__ = True

    dc = mgmt_conf.DATA_CENTERS[6][0]
    ext_cls_0 = mgmt_conf.CLUSTERS[6][0]
    ext_cls_1 = mgmt_conf.CLUSTERS[6][1]
    ext_cls_2 = mgmt_conf.CLUSTERS[6][2]
    ext_cls_3 = mgmt_conf.CLUSTERS[6][3]
    net_1 = mgmt_conf.NETS[6][0]
    net_2 = mgmt_conf.NETS[6][1]
    net_dict = mgmt_conf.NET_DICT_CASE_06
    add_clusters_to_dcs_params = [
        (ext_cls_0, dc, conf.MGMT_BRIDGE), (ext_cls_1, dc, net_1),
        (ext_cls_2, dc, net_2)
    ]
    create_and_attach_network_params = [[(dc, None)], net_dict]
    create_basic_setup_params = [dc, None]
    remove_clusters_params = [ext_cls_3]

    @polarion("RHEVM3-6477")
    def test_01_different_mgmt_net(self):
        """
        1.  Add new cluster without providing explicitly management network
        2.  Check that the default management network exists on that cluster
        3.  Remove clusters with default management network
        4.  Remove Default management network
        5.  Negative: Try to add a new cluster without providing explicitly
            management network
        6.  Add a new cluster with net1 management network provided explicitly
        """
        testflow.step(
            'Add new cluster without providing explicitly management network'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_3, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Check that the default management network exists on that cluster'
        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_3, network=conf.MGMT_BRIDGE
        )

        testflow.step('Remove clusters with default management network')
        for cl in [self.ext_cls_0, self.ext_cls_3]:
            assert ll_clusters.removeCluster(positive=True, cluster=cl)

        testflow.step('Remove Default management network')
        assert ll_networks.remove_network(
            positive=True, network=conf.MGMT_BRIDGE, data_center=self.dc
        )

        testflow.step(
            'Negative: Try to add a new cluster without providing explicitly'
            ' management network'
        )
        assert ll_clusters.addCluster(
            positive=False, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Add a new cluster with net1 management network provided '
            'explicitly'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION,
            management_network=self.net_1
        )

    @polarion("RHEVM3-6478")
    def test_02_same_mgmt_net(self):
        """
        1.  Update all clusters to have net1 as management network
        2.  Add a new cluster without providing explicitly management network
        3.  Check that net1 is management network for a new cluster
        """
        testflow.step('Update all clusters to have net1 as management network')
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cls_2)
        assert ll_networks.remove_network(
            positive=True, network=self.net_2, data_center=self.dc
        )

        testflow.step(
            'Add a new cluster without providing explicitly management'
            ' network'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_3, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Check that net1 is management network for a new cluster'
        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_3, network=self.net_1
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_basic_setup.__name__,
    create_and_attach_network.__name__,
    remove_network.__name__
)
class TestMGMTNetRole07(NetworkTest):
    """
    1.  Create new cluster when one network exists on the DC and check that
        this network becomes management network
    2.  Remove Cluster and then the network from DC
    3.  Negative: Try to add a new cluster when there is no network on DC
    """
    __test__ = True

    dc = mgmt_conf.DATA_CENTERS[7][0]
    net_1 = mgmt_conf.NETS[7][0]
    net_2 = mgmt_conf.NETS[7][1]
    ext_cls_0 = mgmt_conf.CLUSTERS[7][0]
    net_dict = mgmt_conf.NET_DICT_CASE_07
    remove_network_params = [dc, conf.MGMT_BRIDGE]
    create_and_attach_network_params = [[(dc, None)], net_dict]
    create_basic_setup_params = [dc, None]

    @polarion("RHEVM3-6479")
    def test_01_different_mgmt_net(self):
        """
        1.  Add new cluster without providing explicitly management network
        2.  Check that the non-default management network exists on that
            cluster
        3.  Remove cluster
        4.  Remove non-default management network
        5.  Negative: Try to add a new cluster when there is no network on DC
        """
        testflow.step(
            'Add new cluster without providing explicitly management network'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Check that the non-default management network exists on that'
            ' cluster'

        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_0, network=self.net_1
        )

        testflow.step('Remove cluster')
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cls_0)

        testflow.step('Remove non-default management network')
        assert ll_networks.remove_network(
            positive=True, network=self.net_1, data_center=self.dc
        )

        testflow.step(
            'Negative: Try to add a new cluster when there is no network on DC'
        )
        assert ll_clusters.addCluster(
            positive=False, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.dc, version=conf.COMP_VERSION
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    install_host_with_new_management.__name__,
    create_and_attach_network.__name__,
    add_clusters_to_dcs.__name__,
    add_networks_to_clusters.__name__,
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestMGMTNetRole08(NetworkTest):
    """
    1.  Create a new DC and cluster with non-default management network
    2.  Add a new host to this DC/Cluster
    3.  Check that management network of the Host is the network that resides
        on setup
    4.  Move the host to another cluster with the same management network
        (conf.NET_1)
    5.  Try to move the host to the setup with default management network
    6.  Try to change the non-default management to the default one, when the
        Host is attached to the cluster
    7.  Return host to its original DC/Cluster
    8.  Change management network on Extra Cluster to net1
    9.  Check that the change succeeded
    """
    __test__ = True

    dc = mgmt_conf.DATA_CENTERS[8][0]
    ext_cls_0 = mgmt_conf.CLUSTERS[8][0]
    ext_cls_1 = mgmt_conf.CLUSTERS[8][1]
    ext_cls_2 = mgmt_conf.CLUSTERS[8][2]
    net_1 = mgmt_conf.NETS[8][0]
    net_2 = mgmt_conf.NETS[8][1]
    net_dict = mgmt_conf.NET_DICT_CASE_08_2
    add_clusters_to_dcs_params = [
        (ext_cls_1, dc, net_1), (ext_cls_2, dc, net_2),
    ]
    add_networks_to_clusters_params = [(ext_cls_1, net_2), (ext_cls_2, net_1)]
    create_and_attach_network_params = [[(dc, None)], net_dict]
    install_host_with_new_management_params = [
        1, net_1, conf.CL_0, ext_cls_0, dc, mgmt_conf.NET_DICT_CASE_08_1, net_1
    ]
    remove_clusters_params = [ext_cls_1, ext_cls_2]

    @polarion("RHEVM3-6470")
    def test_01_default_mgmt_net(self):
        """
        Check that the non-default management network exists on host
        """
        testflow.step(
            'Check that the non-default management network exists on host'
        )
        assert conf.VDS_1_HOST.network.find_mgmt_interface() == self.net_1

    @polarion("RHEVM3-6467")
    def test_02_moving_host(self):
        """
        1.  Deactivate host
        2.  Move the host to another cluster with the same management network
            (net_1)
        3.  Try to move the host to the setup with net_2 as management network
        """
        host_1 = conf.HOST_1_NAME

        testflow.step('Deactivate host')
        assert ll_hosts.deactivateHost(positive=True, host=host_1)

        testflow.step(
            'Move the host to another cluster with the same management '
            'network (net_1)'
        )
        assert helper.move_host_new_cl(host=host_1, cl=self.ext_cls_1)

        testflow.step(
            'Try to move the host to the setup with net_2 as management '
            'network'
        )
        assert helper.move_host_new_cl(
            host=host_1, cl=self.ext_cls_2, positive=False
        )

    @polarion("RHEVM3-6472")
    def test_03_change_mgmt_net(self):
        """
        1.  Try to change the non-default management to the default one, when
            the Host is attached to the cluster
        2.  Move host to its original DC/Cluster
        3.  Change management network on Extra Cluster to net1
        4.  Check that the change succeeded
        """
        testflow.step(
            'Try to change the non-default management to the default one, '
            'when the Host is attached to the cluster'
        )
        assert ll_networks.update_cluster_network(
            positive=False, cluster=self.ext_cls_1, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_0, network=self.net_1
        )

        testflow.step('Move host to its original DC/Cluster')
        assert helper.move_host_new_cl(
            host=conf.HOST_1_NAME, cl=self.ext_cls_0
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=self.ext_cls_1, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that the change succeeded')
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_1, network=self.net_2
        )
