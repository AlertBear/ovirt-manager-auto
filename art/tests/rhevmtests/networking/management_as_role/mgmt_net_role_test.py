#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing  Management network as a role feature
Several DCs, several clusters with/without the host will be created
"""

import logging

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as conf
import helper
from art.core_api import apis_exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr
from fixtures import *  # flake8: noqa
from _pytest_art.marks import tier2

logger = logging.getLogger("MGMT_Net_Role_Cases")


@tier2
@attr(tier=2)
class TestMGMTNetRole01(NetworkTest):
    """
    Create a new DC and cluster
    Check that management of DC and cluster is the default management
        (ovirtmgmt)
    """
    __test__ = True
    cluster = conf.EXTRA_CLUSTER_0
    dc = conf.EXT_DC_0

    @classmethod
    def setup_class(cls):
        """
        Create a new DC and a new cluster
        """
        helper.create_setup(dc=cls.dc, cl=cls.cluster)

    @polarion("RHEVM3-6466")
    def test_default_mgmt_net(self):
        """
        Check that the default management network exists on DC
        Check that the default management network exists on cluster
        """
        management_network_obj = ll_networks.get_management_network(
            cluster_name=self.cluster
        )
        if not management_network_obj:
            raise conf.NET_EXCEPTION()

        if not ll_networks.get_network_in_datacenter(
            network=management_network_obj.name, datacenter=self.dc
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and cluster
        """
        hl_networks.remove_basic_setup(datacenter=cls.dc, cluster=cls.cluster)


@tier2
@attr(tier=2)
class TestMGMTNetRole02(NetworkTest):
    """
    Try to update default management to network that is non-required
    Update default management to network that is required

    """
    __test__ = True
    dc = conf.DC_0
    cluster = conf.EXTRA_CLUSTER_0
    mgmt = conf.MGMT
    net_1 = conf.NET_1
    net_2 = conf.NET_2

    @classmethod
    def setup_class(cls):
        """
        Create a new cluster
        Create required network
        Create non-required network
        """
        helper.add_cluster()
        local_dict = {
            cls.net_1: {
                "required": "true"
            },
            cls.net_2: {
                "required": "false"
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=cls.dc, cluster=cls.cluster, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6474")
    def test_req_non_req_mgmt_net(self):
        """
        Update management network to be required network sw1
        Check that management network is sw1
        Try to update management network to be non-required network sw2
        Check that management network is still sw1
        """
        if not ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster, network=self.net_1,
            usages=self.mgmt
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            network=self.net_1, cluster_name=self.cluster
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.net_2,
            usages=self.mgmt
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            network=self.net_1, cluster_name=self.cluster
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove required and non-required networks
        """
        ll_clusters.removeCluster(positive=True, cluster=cls.cluster)
        hl_networks.remove_all_networks(datacenter=cls.dc)


@tier2
@attr(tier=2)
class TestMGMTNetRole03(NetworkTest):
    """
    Try to remove default management network when it is attached to cluster
    Remove default management network when it is detached from all clusters
        in the DC

    """
    __test__ = True
    dc = conf.EXT_DC_0
    cluster_0 = conf.EXTRA_CLUSTER_0
    cluster_1 = conf.EXTRA_CLUSTER_1
    net = conf.NET_1

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and 2 clusters for that DC
        2. Create required network for DC and both clusters
        """
        helper.create_setup(dc=cls.dc, cl=cls.cluster_0)
        helper.add_cluster(cl=cls.cluster_1, dc=cls.dc)

        # attach network to both clusters after adding it to DC
        for (dc, cl) in ((cls.dc, cls.cluster_0), (None, cls.cluster_1)):
            if not hl_networks.createAndAttachNetworkSN(
                data_center=dc, cluster=cl, network_dict=conf.NET_DICT
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6476")
    def test_remove_mgmt_net(self):
        """
        Update the first cluster to have sw1 as its management
        Check that management network is sw1 for that cluster
        Try to remove the default management network and fail
        Update the second cluster to have sw1 as its management
        Check that management network is sw1 for that cluster
        Remove the default management network
        Try to remove sw1 and fail
        """
        if not ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster_0, network=self.net,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            cluster_name=self.cluster_0, network=self.net
        ):
            raise conf.NET_EXCEPTION()

        helper.remove_net(net=conf.MGMT_BRIDGE, positive=False, teardown=False)
        if not ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster_1, network=self.net,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            cluster_name=self.cluster_1, network=self.net
        ):
            raise conf.NET_EXCEPTION()

        helper.remove_net(net=conf.MGMT_BRIDGE, teardown=False)
        helper.remove_net(positive=False, teardown=False)

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove additional cluster and DC
        """
        ll_clusters.removeCluster(positive=True, cluster=cls.cluster_0)
        hl_networks.remove_basic_setup(
            datacenter=cls.dc, cluster=cls.cluster_1
        )


@tier2
@attr(tier=2)
class TestMGMTNetRole04(NetworkTest):
    """
    Display and/or migration network fallback
    Management network becomes display network when original display network
        is removed
    Management network becomes migration network when original migration
        network is removed
    """
    __test__ = True
    cluster = conf.EXTRA_CLUSTER_0
    dc = conf.DC_0
    net_1 = conf.NET_1
    net_2 = conf.NET_2
    net_3 = conf.NET_3
    display = "display"
    migration = "migration"
    attrs = [display, migration]

    @classmethod
    def setup_class(cls):
        """
        Create a new cluster
        Create sw1
        Create sw2 as display network
        Create sw3 as migration network
        Update sw1 to be management network
        """
        helper.add_cluster()
        local_dict = {
            cls.net_1: {
                "required": "true"
            },
            cls.net_2: {
                "required": "true",
                "cluster_usages": cls.migration
            },
            cls.net_3: {
                "required": "true",
                "cluster_usages": cls.display
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=cls.dc, cluster=cls.cluster, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_cluster_network(
            positive=True, cluster=cls.cluster, network=cls.net_1,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6469")
    def test_display_migration_fallback(self):
        """
        Remove sw2 from setup
        Check that sw1 is display network
        Remove sw3 network
        Check that sw1 is migration network
        """
        for net in [self.net_2, self.net_3]:
            helper.remove_net(net=net, dc=self.dc, teardown=False)

        if not ll_networks.check_network_usage(
            self.cluster, self.net_1, *self.attrs
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove the network
        """
        ll_clusters.removeCluster(positive=True, cluster=cls.cluster)
        helper.remove_net(dc=cls.dc)


@tier2
@attr(tier=2)
class TestMGMTNetRole05(NetworkTest):
    """
    Move the host between clusters with the same management network
    Negative: Try to move host between clusters with different management
        networks
    """
    __test__ = True
    dc = conf.DC_0
    net = conf.NET_1
    local_dict = conf.NET_DICT
    cluster_0 = conf.EXTRA_CLUSTER_0
    cluster_1 = conf.CL_1
    orig_cluster = conf.CL_0

    @classmethod
    def setup_class(cls):
        """
        1. Create sw1 network on DC
        2. Create a new cluster with sw1 as management network
        """
        if not hl_networks.createAndAttachNetworkSN(
            data_center=cls.dc, network_dict=cls.local_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.add_cluster(management_network=cls.net)

    @polarion("RHEVM3-6471")
    def test_moving_host(self):
        """
        Move the host to another cluster with the default management network
        Negative: Try to move the host to the cluster with non-default
            management network
        """
        if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        helper.move_host_new_cl(host=conf.HOST_1_NAME, cl=self.cluster_1)

        if not ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        helper.move_host_new_cl(
            host=conf.HOST_1_NAME, cl=self.cluster_0, positive=False
        )

    @classmethod
    def teardown_class(cls):
        """
        Move Host to its original cluster
        Remove the cluster
        Remove network sw1
        """
        logger.info("Move the Host to %s", cls.orig_cluster)
        if not ll_hosts.updateHost(
            positive=True, host=conf.HOST_1_NAME, cluster=cls.orig_cluster
        ):
            logger.error(
                "Cannot move host %s to cluster %s", conf.HOST_1_NAME,
                cls.orig_cluster
            )
        if not ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME):
            logger.error()

        ll_clusters.removeCluster(positive=True, cluster=cls.cluster_0)
        helper.remove_net(dc=cls.dc)


@tier2
@attr(tier=2)
class TestMGMTNetRole06(NetworkTest):
    """
    Create a new DC and 3 clusters with default, sw1 and sw2 management
        networks respectively
    Create a new cluster on that DC without explicitly providing management
        and make sure default management was picked up for this cluster
    Remove clusters with default management networks and remove default
        management network
    Try to create a new cluster without providing management network
        explicitly and fail
    Create a new cluster when providing sw1 as management network
    """
    __test__ = True
    dc_ext = conf.EXT_DC_0
    dc = conf.DC_0
    cluster_0 = conf.EXTRA_CLUSTER_0
    cluster_1 = conf.EXTRA_CLUSTER_1
    cluster_2 = conf.EXTRA_CLUSTER_2
    cluster_3 = conf.EXTRA_CLUSTER_3
    net_1 = conf.NET_1
    net_2 = conf.NET_2
    mgmt_net = conf.MGMT_BRIDGE
    cluster_list = [cluster_0, cluster_1, cluster_2]
    net_list = [mgmt_net, net_1, net_2]

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster
        2. Create 2 networks on DC
        3. Create 2 new Clusters with management networks from step 2
        """
        helper.create_setup(dc=cls.dc_ext)

        local_dict = {
            cls.net_1: {
                "required": "true"
            },
            cls.net_2: {
                "required": "true"
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=cls.dc_ext, network_dict=local_dict
        ):
            raise conf.NET_EXCEPTION()

        for cl, net in zip(cls.cluster_list, cls.net_list):
            helper.add_cluster(cl=cl, dc=cls.dc_ext, management_network=net)

    @polarion("RHEVM3-6477")
    def test_different_mgmt_net(self):
        """
        Add new cluster without providing explicitly management network
        Check that the default management network exists on that cluster
        Remove clusters with default management network
        Remove Default management network
        Negative: Try to add a new cluster without providing explicitly
            management network
        Add a new cluster with sw1 management network provided explicitly
        """
        helper.add_cluster(cl=self.cluster_3, dc=self.dc)
        if not hl_networks.is_management_network(
            cluster_name=self.cluster_3, network=self.mgmt_net
        ):
            raise conf.NET_EXCEPTION()

        for cl in [self.cluster_0, self.cluster_3]:
            if not ll_clusters.removeCluster(positive=True, cluster=cl):
                raise conf.NET_EXCEPTION()

        helper.remove_net(net=self.mgmt_net, dc=self.dc_ext, teardown=False)

        helper.add_cluster(cl=self.cluster_0, dc=self.dc_ext, positive=False)
        helper.add_cluster(
            cl=self.cluster_0, dc=self.dc_ext, management_network=self.net_1
        )

    @polarion("RHEVM3-6478")
    def test_same_mgmt_net(self):
        """
        Update all clusters to have sw1 as management network
        Add a new cluster without providing explicitly management network
        Check that sw1 is management network for a new cluster
        """
        if not ll_clusters.removeCluster(
            positive=True, cluster=self.cluster_2
        ):
            raise conf.NET_EXCEPTION()

        helper.remove_net(net=self.net_2, dc=self.dc_ext, teardown=False)
        helper.add_cluster(cl=self.cluster_3, dc=self.dc_ext)

        if not hl_networks.is_management_network(
            cluster_name=self.cluster_3, network=self.net_1
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and clusters
        """
        for cl in cls.cluster_list + [cls.cluster_3]:
            try:
                ll_clusters.removeCluster(positive=True, cluster=cl)
            except apis_exceptions.EntityNotFound:
                logger.error("Cluster %s doesn't exist in the setup", cl)

        hl_networks.remove_basic_setup(datacenter=cls.dc_ext)


@tier2
@attr(tier=2)
class TestMGMTNetRole07(NetworkTest):
    """
    Create new cluster when one network exists on the DC and check that this
        network becomes management network
    Remove Cluster and then the network from DC
    Negative: Try to add a new cluster when there is no network on DC
    """
    __test__ = True
    dc = conf.EXT_DC_0
    net = conf.NET_1
    cluster = conf.EXTRA_CLUSTER_0
    mgmt_net = conf.MGMT_BRIDGE
    net_dict = conf.NET_DICT

    @classmethod
    def setup_class(cls):
        """
        Create a new DC
        Create network on DC
        Remove default management network
        """
        helper.create_setup(dc=cls.dc)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=cls.dc,  network_dict=cls.net_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.remove_net(net=cls.mgmt_net, teardown=False)

    @polarion("RHEVM3-6479")
    def test_different_mgmt_net(self):
        """
        Add new cluster without providing explicitly management network
        Check that the non-default management network exists on that cluster
        Remove cluster
        Remove non-default management network
        Negative: Try to add a new cluster when there is no network on DC
        """
        helper.add_cluster(dc=self.dc)
        if not hl_networks.is_management_network(
            cluster_name=self.cluster, network=self.net
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            cluster_name=self.cluster, network=self.net
        ):
            raise conf.NET_EXCEPTION()

        if not ll_clusters.removeCluster(positive=True, cluster=self.cluster):
            raise conf.NET_EXCEPTION()

        helper.remove_net(teardown=False)
        helper.add_cluster(dc=self.dc, positive=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        hl_networks.remove_basic_setup(datacenter=cls.dc)


@tier2
@attr(tier=2)
@pytest.mark.usefixtures("prepare_setup_case_08")
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestMGMTNetRole08(NetworkTest):
    """
    Create a new DC and cluster with non-default management network
    Add a new host to this DC/Cluster
    Check that management network of the Host is the network that resides
        on setup
    Move the host to another cluster with the same management network
        (conf.NET_1)
    Try to move the host to the setup with default management network
    Try to change the non-default management to the default one, when the
        Host is attached to the cluster
    Return host to its original DC/Cluster
    Change management network on Extra Cluster to net1
    Check that the change succeeded
    """
    __test__ = True
    cluster_0 = conf.EXTRA_CL[0]
    cluster_1 = conf.EXTRA_CL[1]
    cluster_2 = conf.EXTRA_CL[2]
    net_1 = conf.NET_1
    net_2 = conf.NET_2

    @polarion("RHEVM3-6470")
    def test_01_default_mgmt_net(self):
        """
        Check that the non-default management network exists on host
        """
        if not conf.VDS_1_HOST.network.find_mgmt_interface() == self.net_1:
            raise conf.NET_EXCEPTION(
                "Host should have %s as its MGMT network" % self.net_1
            )

    @polarion("RHEVM3-6467")
    def test_02_moving_host(self):
        """
        Deactivate host
        Move the host to another cluster with the same management network
            (net_1)
        Try to move the host to the setup with net_2 as management network
        """
        if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        helper.move_host_new_cl(host=conf.HOST_1_NAME, cl=self.cluster_1)
        helper.move_host_new_cl(
            host=conf.HOST_1_NAME, cl=self.cluster_2, positive=False,
        )

    @polarion("RHEVM3-6472")
    def test_03_change_mgmt_net(self):
        """
        Try to change the non-default management to the default one, when the
            Host is attached to the cluster
        Return host to its original DC/Cluster
        Change management network on Extra Cluster to net1
        Check that the change succeeded
        """
        if not ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster_1, network=self.net_2,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            cluster_name=self.cluster_0, network=self.net_1
        ):
            raise conf.NET_EXCEPTION()

        helper.move_host_new_cl(host=conf.HOST_1_NAME, cl=self.cluster_0)

        if not ll_networks.update_cluster_network(
            positive=True, cluster=self.cluster_1, network=self.net_2,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.is_management_network(
            cluster_name=self.cluster_1, network=self.net_2
        ):
            raise conf.NET_EXCEPTION()
