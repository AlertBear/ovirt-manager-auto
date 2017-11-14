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
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import (
    add_networks_to_clusters, move_host_to_cluster,
    remove_network, install_host_with_new_management
)
from rhevmtests.fixtures import create_clusters, create_datacenters
from rhevmtests.networking.fixtures import (  # noqa: F401
    remove_all_networks,
    update_cluster_network_usages,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_clusters.__name__
)
class TestMGMTNetRole01(NetworkTest):
    """
    1.  Create DC and cluster
    2.  Check that the management of the DC and cluster is the default
            management network (ovirtmgmt)
    """

    ext_dc = mgmt_conf.DATA_CENTERS[1][0]
    ext_cluster = mgmt_conf.CLUSTERS[1][0]
    clusters_dict = {
        ext_cluster: {
            "name": ext_cluster,
            "data_center": ext_dc,
            "version": conf.COMP_VERSION,
            "cpu": conf.CPU_NAME,
        }
    }
    datacenters_dict = {
        ext_dc: {
            "name": ext_dc,
            "version": conf.COMP_VERSION,
        }
    }

    @tier2
    @polarion("RHEVM3-6466")
    def test_01_default_mgmt_net(self):
        """
        1.  Check that the default management network exists on DC
        2.  Check that the default management network exists on cluster
        """
        testflow.step('Check that the default management network exists on DC')
        management_network_obj = ll_networks.get_management_network(
            cluster_name=self.ext_cluster
        )
        assert management_network_obj

        testflow.step(
            'Check that the default management network exists on cluster'
        )
        assert ll_networks.get_network_in_datacenter(
            network=management_network_obj.name, datacenter=self.ext_dc
        )


@pytest.mark.usefixtures(
    create_clusters.__name__,
    create_and_attach_networks.__name__
)
class TestMGMTNetRole02(NetworkTest):
    """
    1.  Try to update default management to network that is non-required
    2.  Update default management to network that is required
    """

    dc = conf.DC_0
    cluster = mgmt_conf.CLUSTERS[2][0]
    net_1 = mgmt_conf.NETS[2][0]
    net_2 = mgmt_conf.NETS[2][1]

    # create_clusters params
    clusters_dict = {
        cluster: {
            "name": cluster,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": mgmt_conf.NET_DICT_CASE_02
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier2
    @polarion("RHEVM3-6474")
    def test_01_req_non_req_mgmt_net(self):
        """
        1.  Update management network to be required network net1
        2.  Check that management network is net1
        3.  Try to update management network to be non-required network net2
        4.  Check that management network is still net1
        """
        cluster_obj = ll_clusters.get_cluster_object(cluster_name=self.cluster)
        testflow.step('Update management network to be required network net1')
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=self.net_1,
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
            positive=False, cluster=cluster_obj, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is still net1')
        assert hl_networks.is_management_network(
            network=self.net_1, cluster_name=self.cluster
        )


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_clusters.__name__,
    create_and_attach_networks.__name__
)
class TestMGMTNetRole03(NetworkTest):
    """
    1.  Try to remove default management network when it is attached to cluster
    2.  Remove default management network when it is detached from all clusters
            in the DC
    """

    ext_cluster = mgmt_conf.CLUSTERS[3][0]
    ext_cluster_1 = mgmt_conf.CLUSTERS[3][1]
    ext_dc = mgmt_conf.DATA_CENTERS[3][0]
    net_1 = mgmt_conf.NETS[3][0]

    # create_datacenters params
    datacenters_dict = {
        ext_dc: {
            "name": ext_dc,
            "version": conf.COMP_VERSION,
        }
    }

    # create_clusters params
    clusters_dict = {
        ext_cluster: {
            "name": ext_cluster,
            "data_center": ext_dc,
            "version": conf.COMP_VERSION,
            "cpu": conf.CPU_NAME,
        },
        ext_cluster_1: {
            "name": ext_cluster_1,
            "data_center": ext_dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": ext_dc,
            "clusters": [ext_cluster, ext_cluster_1],
            "networks": mgmt_conf.NET_DICT_CASE_03
        },
    }

    @tier2
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
        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.ext_cluster
        )
        cluster_1_obj = ll_clusters.get_cluster_object(
            cluster_name=self.ext_cluster_1
        )
        testflow.step(
            'Update the first cluster to have net1 as its management'
        )

        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=self.net_1,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that management network is net1 for that cluster')
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cluster, network=self.net_1
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
            positive=True, cluster=cluster_1_obj, network=self.net_1,
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


@pytest.mark.usefixtures(
    create_clusters.__name__,
    create_and_attach_networks.__name__,
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

    net_1 = mgmt_conf.NETS[4][0]
    net_2 = mgmt_conf.NETS[4][1]
    net_3 = mgmt_conf.NETS[4][2]
    dc = conf.DC_0
    ext_cls_0 = mgmt_conf.DATA_CENTERS[4][0]

    # update_cluster_network_usages
    update_cluster = ext_cls_0
    update_cluster_network = net_1
    update_cluster_network_usages = conf.MANAGEMENT_NET_USAGE

    # create_clusters params
    clusters_dict = {
        ext_cls_0: {
            "name": ext_cls_0,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
        }
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [ext_cls_0],
            "networks": mgmt_conf.NET_DICT_CASE_04
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    usages_to_check = [conf.DISPLAY_NET_USAGE, conf.MIGRATION_NET_USAGE]

    @tier2
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

        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.ext_cls_0
        )
        testflow.step('Checking network usages')
        assert ll_networks.check_network_usage(
            cluster=cluster_obj, network=self.net_1, attrs=self.usages_to_check
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    create_clusters.__name__,
    move_host_to_cluster.__name__
)
class TestMGMTNetRole05(NetworkTest):
    """
    1.  Move the host between clusters with the same management network
    2.  Negative: try to move host between clusters with different management
        networks
    """

    dc = conf.DC_0
    ext_cls_0 = mgmt_conf.CLUSTERS[5][0]
    ext_cls_1 = mgmt_conf.CLUSTERS[5][1]
    net_1 = mgmt_conf.NETS[5][0]

    # move_host_to_cluster params
    move_host_to_cluster_params = [2, conf.CL_0]

    # create_clusters params
    clusters_dict = {
        ext_cls_0: {
            "name": ext_cls_0,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": net_1
        },
        ext_cls_1: {
            "name": ext_cls_1,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
        }
    }
    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "networks": mgmt_conf.NET_DICT_CASE_05
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier2
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
        assert ll_hosts.deactivate_host(positive=True, host=conf.HOST_2_NAME)
        assert helper.move_host_new_cl(
            host=conf.HOST_2_NAME, cl=self.ext_cls_1
        )
        assert ll_hosts.activate_host(positive=True, host=conf.HOST_2_NAME)
        assert ll_hosts.deactivate_host(positive=True, host=conf.HOST_2_NAME)

        testflow.step(
            'Negative: try to move the host to the cluster with non-default'
            ' management network'
        )
        assert helper.move_host_new_cl(
            host=conf.HOST_2_NAME, cl=self.ext_cls_0, positive=False
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_and_attach_networks.__name__,
    create_clusters.__name__,
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

    ext_dc = mgmt_conf.DATA_CENTERS[6][0]
    ext_cls_0 = mgmt_conf.CLUSTERS[6][0]
    ext_cls_1 = mgmt_conf.CLUSTERS[6][1]
    ext_cls_2 = mgmt_conf.CLUSTERS[6][2]
    ext_cls_3 = mgmt_conf.CLUSTERS[6][3]
    net_1 = mgmt_conf.NETS[6][0]
    net_2 = mgmt_conf.NETS[6][1]

    # create_datacenters params
    datacenters_dict = {
        ext_dc: {
            "name": ext_dc,
            "version": conf.COMP_VERSION,
        }
    }
    # create_clusters params
    clusters_to_remove = [ext_cls_0, ext_cls_1, ext_cls_3]
    clusters_dict = {
        ext_cls_0: {
            "name": ext_cls_0,
            "data_center": ext_dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": conf.MGMT_BRIDGE
        },
        ext_cls_1: {
            "name": ext_cls_1,
            "data_center": ext_dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": net_1
        },
        ext_cls_2: {
            "name": ext_cls_2,
            "data_center": ext_dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": net_2
        },
    }

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": ext_dc,
            "networks": mgmt_conf.NET_DICT_CASE_06
        }
    }

    @tier2
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
            data_center=self.ext_dc, version=conf.COMP_VERSION
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
            positive=True, network=conf.MGMT_BRIDGE, data_center=self.ext_dc
        )

        testflow.step(
            'Negative: Try to add a new cluster without providing explicitly'
            ' management network'
        )
        assert ll_clusters.addCluster(
            positive=False, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.ext_dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Add a new cluster with net1 management network provided '
            'explicitly'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.ext_dc, version=conf.COMP_VERSION,
            management_network=self.net_1
        )

    @tier2
    @polarion("RHEVM3-6478")
    def test_02_same_mgmt_net(self):
        """
        1.  Update all clusters to have net1 as management network
        2.  Add a new cluster without providing explicitly management network
        3.  Check that net1 is management network for a new cluster
        """
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cls_2)
        assert ll_networks.remove_network(
            positive=True, network=self.net_2, data_center=self.ext_dc
        )

        testflow.step(
            'Add a new cluster without providing explicitly management'
            ' network'
        )
        assert ll_clusters.addCluster(
            positive=True, name=self.ext_cls_3, cpu=conf.CPU_NAME,
            data_center=self.ext_dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Check that net1 is management network for a new cluster'
        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_3, network=self.net_1
        )


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_and_attach_networks.__name__,
    remove_network.__name__
)
class TestMGMTNetRole07(NetworkTest):
    """
    1.  Create new cluster when one network exists on the DC and check that
        this network becomes management network
    2.  Remove Cluster and then the network from DC
    3.  Negative: Try to add a new cluster when there is no network on DC
    """

    ext_dc = mgmt_conf.DATA_CENTERS[7][0]
    net_1 = mgmt_conf.NETS[7][0]
    net_2 = mgmt_conf.NETS[7][1]
    ext_cls_0 = mgmt_conf.CLUSTERS[7][0]

    # create_datacenters params
    datacenters_dict = {
        ext_dc: {
            "name": ext_dc,
            "version": conf.COMP_VERSION,
        }
    }
    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": ext_dc,
            "networks": mgmt_conf.NET_DICT_CASE_07
        }
    }

    # remove_network params
    remove_network_params = [ext_dc, conf.MGMT_BRIDGE]

    @tier2
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
            data_center=self.ext_dc, version=conf.COMP_VERSION
        )

        testflow.step(
            'Check that the non-default management network exists on that'
            ' cluster'

        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_0, network=self.net_1
        )

        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cls_0)

        testflow.step('Remove non-default management network')
        assert ll_networks.remove_network(
            positive=True, network=self.net_1, data_center=self.ext_dc
        )

        testflow.step(
            'Negative: Try to add a new cluster when there is no network on DC'
        )
        assert ll_clusters.addCluster(
            positive=False, name=self.ext_cls_0, cpu=conf.CPU_NAME,
            data_center=self.ext_dc, version=conf.COMP_VERSION
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    install_host_with_new_management.__name__,
    create_and_attach_networks.__name__,
    create_clusters.__name__,
    add_networks_to_clusters.__name__,
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.skip("Move host fails, need more investigation")
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

    dc = mgmt_conf.DATA_CENTERS[8][0]
    ext_cls_0 = mgmt_conf.CLUSTERS[8][0]
    ext_cls_1 = mgmt_conf.CLUSTERS[8][1]
    ext_cls_2 = mgmt_conf.CLUSTERS[8][2]
    net_1 = mgmt_conf.NETS[8][0]
    net_2 = mgmt_conf.NETS[8][1]

    # create_clusters params
    clusters_dict = {
        ext_cls_1: {
            "name": ext_cls_1,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": net_1
        },
        ext_cls_2: {
            "name": ext_cls_2,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION,
            "management_network": net_2
        },
    }

    # add_networks_to_clusters params
    add_networks_to_clusters_params = [(ext_cls_1, net_2), (ext_cls_2, net_1)]

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "networks": mgmt_conf.NET_DICT_CASE_08_2
        }
    }

    # install_host_with_new_management params
    install_host_with_new_management_params = [
        2, net_1, conf.CL_0, ext_cls_0, dc, mgmt_conf.NET_DICT_CASE_08_1, net_1
    ]

    @tier2
    @polarion("RHEVM3-6470")
    def test_01_default_mgmt_net(self):
        """
        Check that the non-default management network exists on host
        """
        testflow.step(
            'Check that the non-default management network exists on host'
        )
        assert conf.VDS_2_HOST.network.find_mgmt_interface() == self.net_1

    @tier2
    @polarion("RHEVM3-6467")
    def test_02_moving_host(self):
        """
        1.  Deactivate host
        2.  Move the host to another cluster with the same management network
            (net_1)
        3.  Try to move the host to the setup with net_2 as management network
        """
        host_2 = conf.HOST_2_NAME

        testflow.step('Deactivate host')
        assert ll_hosts.deactivate_host(positive=True, host=host_2)

        testflow.step(
            'Move the host to another cluster with the same management '
            'network (net_1)'
        )
        assert helper.move_host_new_cl(host=host_2, cl=self.ext_cls_1)

        testflow.step(
            'Try to move the host to the setup with net_2 as management '
            'network'
        )
        assert helper.move_host_new_cl(
            host=host_2, cl=self.ext_cls_2, positive=False
        )

    @tier2
    @polarion("RHEVM3-6472")
    def test_03_change_mgmt_net(self):
        """
        1.  Try to change the non-default management to the default one, when
            the Host is attached to the cluster
        2.  Move host to its original DC/Cluster
        3.  Change management network on Extra Cluster to net1
        4.  Check that the change succeeded
        """
        cluster_obj = ll_clusters.get_cluster_object(
            cluster_name=self.ext_cls_1
        )
        testflow.step(
            'Try to change the non-default management to the default one, '
            'when the Host is attached to the cluster'
        )
        assert ll_networks.update_cluster_network(
            positive=False, cluster=cluster_obj, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_0, network=self.net_1
        )

        testflow.step('Move host to its original DC/Cluster')
        assert helper.move_host_new_cl(
            host=conf.HOST_2_NAME, cl=self.ext_cls_0
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=self.net_2,
            usages=conf.MANAGEMENT_NET_USAGE
        )

        testflow.step('Check that the change succeeded')
        assert hl_networks.is_management_network(
            cluster_name=self.ext_cls_1, network=self.net_2
        )
