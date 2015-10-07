#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing  Management network as a role feature
Several DCs, several clusters with/without the host will be created
"""

import logging
import art.core_api.apis_exceptions as apis_exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import helper

import config as c

logger = logging.getLogger("MGMT_Net_Role_Cases")


@attr(tier=2)
class TestMGMTNetRole01(TestCase):
    """
    1. Create a new DC and cluster
    2. Check that MGMT of DC and cluster is the default MGMT (ovirtmgmt)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster
        """
        helper.create_setup(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0)

    @polarion("RHEVM3-6466")
    def test_default_mgmt_net(self):
        """
        1. Check that the default MGMT network exists on DC
        2. Check that the default MGMT network exists on cluster
        """
        logger.info(
            "Check network %s exists on DC %s", c.MGMT_BRIDGE, c.EXT_DC_0
        )
        if not ll_networks.get_network_in_datacenter(
            c.MGMT_BRIDGE, c.EXT_DC_0
        ):
            raise c.NET_EXCEPTION(
                "Network %s doesn't exist on DC %s" %
                (c.MGMT_BRIDGE, c.EXT_DC_0)
            )

        logger.info(
            "Check network %s exists on cluster %s", c.MGMT_BRIDGE,
            c.EXTRA_CLUSTER_0
        )
        if not ll_networks.get_dc_network_by_cluster(
            c.EXTRA_CLUSTER_0, c.MGMT_BRIDGE
        ):
            raise c.NET_EXCEPTION(
                "Network %s doesn't exist on cluster %s" %
                (c.MGMT_BRIDGE, c.EXTRA_CLUSTER_0)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and cluster
        """
        helper.remove_dc_cluster()


@attr(tier=2)
class TestMGMTNetRole02(TestCase):
    """
    1. Negative: Try to update default MGMT to network that is non-required
    2. Update default MGMT to network that is required

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new cluster
        2. Create required network
        3. Create non-required network
        """

        helper.add_cluster()
        local_dict = {
            c.net1: {"required": "true"},
            c.net2: {"required": "false"}
        }
        helper.create_net_dc_cluster(
            dc=c.ORIG_DC, cl=c.EXTRA_CLUSTER_0, net_dict=local_dict
        )

    @polarion("RHEVM3-6474")
    def test_req_nonreq_mgmt_net(self):
        """
        1. Update MGMT network to be required network sw1
        2. Check that MGMT network is sw1
        3. Try to update MGMT network to be non-required network sw2
        4. Check that MGMT network is still sw1
        """
        helper.update_mgmt_net()
        helper.check_mgmt_net()

        helper.update_mgmt_net(net=c.net2, positive=False)
        logger.info(
            "Check MGMT network on cluster %s is still %s ",
            c.EXTRA_CLUSTER_0, c.net1
        )
        helper.check_mgmt_net()

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove required and non-required networks
        """
        helper.remove_cl()

        logger.info("Remove all networks besides MGMT")
        if not hl_networks.remove_all_networks(
            datacenter=c.ORIG_DC, mgmt_network=c.MGMT_BRIDGE
        ):
            logger.error("Cannot remove networks from setup")


@attr(tier=2)
class TestMGMTNetRole03(TestCase):
    """
    Default MGMT removal
    1. Try to remove default MGMT network when it is attached to cluster
    2. Remove default MGMT network when it is detached from all clusters in
    the DC

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and 2 clusters for that DC
        2. Create required network for DC and both clusters
        """
        helper.create_setup(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0)
        helper.add_cluster(cl=c.EXTRA_CLUSTER_1, dc=c.EXT_DC_0)
        local_dict = {c.net1: {"required": "true"}}
        # attach network to both clusters after adding it to DC
        for (dc, cl) in (
            (c.EXT_DC_0, c.EXTRA_CLUSTER_0), (None, c.EXTRA_CLUSTER_1)
        ):
            helper.create_net_dc_cluster(dc=dc, cl=cl, net_dict=local_dict)

    @polarion("RHEVM3-6476")
    def test_remove_mgmt_net(self):
        """
        1. Update the first cluster to have sw1 as it's MGMT
        2. Check that MGMT network is sw1 for that cluster
        3. Try to remove the default MGMT network and fail
        4. Update the second cluster to have sw1 as it's MGMT
        5. Check that MGMT network is sw1 for that cluster
        6. Remove the default MGMT network
        7. Try to remove sw1 and fail
        """
        helper.update_mgmt_net()
        helper.check_mgmt_net()
        helper.remove_net(net=c.MGMT_BRIDGE, positive=False, teardown=False)
        helper.update_mgmt_net(cl=c.EXTRA_CLUSTER_1)
        helper.check_mgmt_net(cl=c.EXTRA_CLUSTER_1)
        helper.remove_net(net=c.MGMT_BRIDGE, teardown=False)

        logger.info(
            "Try to remove network %s that is a new MGMT", c.net1
        )
        helper.remove_net(positive=False, teardown=False)

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove additional cluster and DC
        """
        helper.remove_cl()
        helper.remove_dc_cluster(cl=c.EXTRA_CLUSTER_1)


@attr(tier=2)
class TestMGMTNetRole04(TestCase):
    """
    Display and/or migration network fallback
    1. MGMT network becomes display network when original display network is
    removed
    2. MGMT network becomes migration network when original migration
    network is removed

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new cluster
        2. Create sw1
        3. Create sw2 as display network
        4. Create sw3 as migration network
        5. Update sw1 to be MGMT network
        """

        helper.add_cluster()
        local_dict = {
            c.net1: {"required": "true"},
            c.net2: {"required": "true", "cluster_usages": "migration"},
            c.net3: {"required": "true", "cluster_usages": "display"}
        }

        helper.create_net_dc_cluster(
            dc=c.ORIG_DC, cl=c.EXTRA_CLUSTER_0, net_dict=local_dict
        )

        helper.update_mgmt_net()

    @polarion("RHEVM3-6469")
    def test_display_migration_fallback(self):
        """
        1. Remove sw2 from setup
        2. Check that sw1 is display network
        3. Remove sw3 network
        4. Check that sw1 is migration network
        """
        logger.info("Remove %s display network", c.net2)
        helper.remove_net(net=c.net2, dc=c.ORIG_DC, teardown=False)

        logger.info("Remove %s migration network", c.net3)
        helper.remove_net(net=c.net3, dc=c.ORIG_DC, teardown=False)

        logger.info(
            "Check that the %s was updated to be migration and display "
            "network", c.net1
        )
        if not ll_networks.check_network_usage(
            c.EXTRA_CLUSTER_0, c.net1, *("display", "migration")
        ):
            raise c.NET_EXCEPTION(
                "Migration and Display Network should be %s, but it's not" %
                c.net1
            )

    @classmethod
    def teardown_class(cls):
        """
        1. Remove the cluster
        2. Remove the network
        """
        helper.remove_cl()
        helper.remove_net(dc=c.ORIG_DC)


@attr(tier=2)
class TestMGMTNetRole05(TestCase):
    """
    Moving host between clusters
    1. Move the host between clusters with the same MGMT network
    2. Negative: Try to move host between clusters with different MGMT networks

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create sw1 network on DC
        2. Create a new cluster with sw1 as MGMT network
        """
        local_dict = {c.net1: {"required": "true"}}

        helper.create_net_dc_cluster(
            dc=c.ORIG_DC, cl=None, net_dict=local_dict
        )

        helper.add_cluster(management_network=c.net1)

    @polarion("RHEVM3-6471")
    def test_moving_host(self):
        """
        1. Move the host to another cluster with the default MGMT network
        2. Negative: Try to move the host to the cluster with non-default
        MGMT network
        """
        logger.info(
            "Deactivate host %s, move it to cluster %s and reactivate it",
            c.HOSTS[0], c.CLUSTER_1
        )
        helper.deactivate_host(host=c.HOSTS[0])
        helper.move_host_new_cl(host=c.HOSTS[0], cl=c.CLUSTER_1)

        if not ll_hosts.activateHost(True, host=c.HOSTS[0]):
            raise c.NET_EXCEPTION("Cannot activate host %s" % c.HOSTS[0])

        logger.info(
            "Negative: Deactivate host %s, and try move it to cluster %s with "
            "non-default MGMT", c.HOSTS[0], c.EXTRA_CLUSTER_0
        )
        helper.deactivate_host(host=c.HOSTS[0])
        helper.move_host_new_cl(
            host=c.HOSTS[0], cl=c.EXTRA_CLUSTER_0, positive=False
        )

    @classmethod
    def teardown_class(cls):
        """
        1. Move Host to its original cluster
        2. Remove the cluster
        3. Remove network sw1
        """
        logger.info("Move the Host to %s", c.CLUSTER_0)
        if not ll_hosts.updateHost(
            True, host=c.HOSTS[0], cluster=c.CLUSTER_0
        ):
            logger.error(
                "Cannot move host %s to cluster %s", c.HOSTS[0],
                c.CLUSTER_0
            )
        if not ll_hosts.activateHost(True, host=c.HOSTS[0]):
            logger.error("Cannot activate host %s", c.HOSTS[0])

        helper.remove_cl()
        helper.remove_net(dc=c.ORIG_DC)


@attr(tier=2)
class TestMGMTNetRole06(TestCase):
    """
    Create a new CL when others CLs have different MGMT networks
    1. Create a new DC and 3 clusters with defualt, sw1 and sw2 MGMT networks
    respectively
    2. Create a new cluster on that DC without explicitly providing MGMT
    and make sure default MGMT was picked up for this cluster
    3. Remove clusters with default MGMT networks and remove default MGMT
    network
    4. Try to create a new cluster without providing MGMT network explicitly
    and fail
    5. Create a new cluster when providing sw1 as MGMT network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster
        2. Create 2 networks on DC
        3. Create 2 new Clusters with MGMT networks from step 2
        """
        helper.create_setup(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_2)

        local_dict = {
            c.net1: {"required": "true"},
            c.net2: {"required": "true"}
        }

        helper.create_net_dc_cluster(
            dc=c.EXT_DC_0, cl=None, net_dict=local_dict
        )

        for i, net in zip(range(2), c.NETWORKS[:2]):
            logger.info("Create a new cluster with %s MGMT network", net)
            helper.add_cluster(
                cl=c.EXTRA_CL[i], dc=c.EXT_DC_0, management_network=net
            )

    @polarion("RHEVM3-6477")
    def test_different_mgmt_net(self):
        """
        1. Add new cluster without providing explicitly MGMT network
        2. Check that the default MGMT network exists on that cluster
        3. Remove clusters with default MGMT network
        4. Remove Default MGMT network
        5. Negative: Try to add a new cluster without providing explicitly
               MGMT network
        6. Add a new cluster with sw1 MGMT network provided explicitly
        """
        logger.info("Create a new cluster without explicitly providing MGMT")
        helper.add_cluster(cl=c.EXTRA_CLUSTER_3, dc=c.ORIG_DC)

        helper.check_mgmt_net(cl=c.EXTRA_CLUSTER_3, net=c.MGMT_BRIDGE)

        logger.info(
            "Remove clusters %s with default MGMT network from DC %s",
            c.EXTRA_CL[2:4], c.EXT_DC_0
        )
        for cl in c.EXTRA_CL[2:4]:
            helper.remove_cl(cl=cl)
        helper.remove_net(net=c.MGMT_BRIDGE, dc=c.EXT_DC_0, teardown=False)

        logger.info(
            "Negative: Try to create a new cluster %s without explicitly "
            "providing MGMT network", c.EXTRA_CLUSTER_2
        )
        helper.add_cluster(cl=c.EXTRA_CLUSTER_2, dc=c.EXT_DC_0, positive=False)
        helper.add_cluster(
            cl=c.EXTRA_CLUSTER_2, dc=c.EXT_DC_0, management_network=c.net1
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC and clusters
        """
        for cl in c.EXTRA_CL[1:3]:
            try:
                helper.remove_cl(cl=cl)
            except apis_exceptions.EntityNotFound:
                logger.error("Cluster %s doesn't exist in the setup", cl)

        helper.remove_dc_cluster()


@attr(tier=2)
class TestMGMTNetRole07(TestCase):
    """
    1. Create a new DC and 3 clusters with defualt  MGMT on first
    cluster and sw1 on 2 other clusters
    2. Create a new cluster on that DC without explicitly providing MGMT
    and make sure default MGMT was picked up for this cluster
    3. Remove clusters with default MGMT networks and remove default MGMT
    network
    4. Create a new cluster without providing MGMT network explicitly
    5. Make sure a new cluster was created with sw1 as its MGMT network
    """
    __test__ = True
    bz = {"1209041": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster
        2. Create new network on DC
        3. Create 2 new Clusters with MGMT network from step 2
        """

        helper.create_setup(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_2)

        local_dict = {
            c.net1: {"required": "true"}
        }

        helper.create_net_dc_cluster(
            dc=c.EXT_DC_0, cl=None, net_dict=local_dict
        )

        for i in range(2):
            helper.add_cluster(
                cl=c.EXTRA_CL[i], dc=c.EXT_DC_0, management_network=c.net1
            )

    @polarion("RHEVM3-6478")
    def test_same_mgmt_net(self):
        """
        1. Add new cluster without providing explicitly MGMT network
        2. Check that the default MGMT network exists on that cluster
        3. Remove clusters with default MGMT network
        4. Remove Default MGMT network
        5. Try to add a new cluster without providing explicitly
               MGMT network
        6. Check that sw1 is MGMT network for a new cluster
        """
        logger.info("Create a new cluster without explicitly providing MGMT")
        helper.add_cluster(cl=c.EXTRA_CLUSTER_3, dc=c.EXT_DC_0)

        helper.check_mgmt_net(cl=c.EXTRA_CLUSTER_3, net=c.MGMT_BRIDGE)

        for cl in c.EXTRA_CL[2:4]:
            helper.remove_cl(cl=cl)

        helper.remove_net(net=c.MGMT_BRIDGE, teardown=False)

        logger.info(
            "Create a new cluster %s without explicitly providing MGMT "
            "network when the same MGMT network exists for all clusters",
            c.EXTRA_CLUSTER_2
        )
        helper.add_cluster(
            cl=c.EXTRA_CLUSTER_2, dc=c.EXT_DC_0, management_network=c.net1
        )
        helper.check_mgmt_net(cl=c.EXTRA_CLUSTER_2)

    @classmethod
    def teardown_class(cls):
        """
        Remove clusters from DC
        Remove the DC and cluster
        """
        for cl in c.EXTRA_CL[1:3]:
            helper.remove_cl(cl=cl)

        helper.remove_dc_cluster()


@attr(tier=2)
class TestMGMTNetRole08(TestCase):
    """
    1. Create a new DC and cluster with non-default MGMT network
    2. Add a new host to this DC/Cluster
    3. Check that MGMT network of the Host is the network that resides on setup
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster with non-default MGMT network and
        install a new Host on it
        """
        helper.install_host_new_mgmt()

    @polarion("RHEVM3-6470")
    def test_default_mgmt_net(self):
        """
        Check that the non-default MGMT network exists on host
        """
        if not c.VDS_HOSTS[-1].network.find_mgmt_interface() == c.net1:
            raise c.NET_EXCEPTION(
                "Host should have %s as its MGMT network" % c.net1
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the Host from the DC/Cluster with c.net1 as MGMT
        Add host back to its original DC/Cluster
        """
        helper.install_host_new_mgmt(
            network=c.net1, dest_cl=c.CLUSTER_1, new_setup=False,
            remove_setup=True
        )


@attr(tier=2)
class TestMGMTNetRole09(TestCase):
    """
    Moving Host between Clusters on different DCs
    1. Move the host between clusters with the same MGMT network (c.net1)
    2. Move the host between clusters with the same MGMT network (c.net1),
    when on one setup c.net1 is tagged and on another setup it's untagged
    3. Negative: Try to move host between setups with different MGMT networks

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster with non-default MGMT network and
        install a new Host on it
        2. Create another DC and Cluster with c.net1 MGMT network
        3. Create another DC and Cluster with c.net1 tagged MGMT network
        """

        local_dict = [
            {c.net1: {"required": "true", "vlan_id": c.VLAN_ID[0]}},
            {c.net1: {"required": "true"}}
        ]
        helper.install_host_new_mgmt()

        logger.info(
            "Create 2 setups with %s as tagged/untagged MGMT network", c.net1
        )
        for i in range(1, 3):
            helper.create_setup(dc=c.EXTRA_DC[i], cl=None)
            helper.create_net_dc_cluster(
                dc=c.EXTRA_DC[i], cl=None, net_dict=local_dict[i-1]
            )
            helper.add_cluster(
                cl=c.EXTRA_CL[i], dc=c.EXTRA_DC[i], management_network=c.net1
            )

    @polarion("RHEVM3-6467")
    def test_moving_host(self):
        """
        1. Move the host to another cluster with the same MGMT network (c.net1)
        2. Move the host to another cluster with the same MGMT network (c.net1)
        but in one setup it's tagged and in another untagged
        2. Negative: Try to move the host to the setup with default MGMT
        network
        """
        for cl in (c.EXTRA_CLUSTER_1, c.EXTRA_CLUSTER_2):
            helper.deactivate_host(host=c.HOSTS[-1])
            helper.move_host_new_cl(
                host=c.HOSTS[-1], cl=cl, activate_host=True
            )

        logger.info(
            "Negative: Deactivate host %s, and try move it to cluster %s with "
            "default MGMT", c.HOSTS[-1], c.CLUSTER_0
        )
        helper.deactivate_host(host=c.HOSTS[-1])
        helper.move_host_new_cl(
            host=c.HOSTS[-1], cl=c.CLUSTER_0, positive=False,
            activate_host=True
        )

    @classmethod
    def teardown_class(cls):
        """
        1. Move Host to its original cluster
        2. Remove the additional DCs and Clusters
        """
        helper.install_host_new_mgmt(
            network=c.net1, dc=c.EXTRA_DC[2], cl=c.EXTRA_CLUSTER_2,
            dest_cl=c.CLUSTER_1, new_setup=False, remove_setup=True
        )
        for i in range(2):
            helper.remove_dc_cluster(dc=c.EXTRA_DC[i], cl=c.EXTRA_CL[i])


@attr(tier=2)
class TestMGMTNetRole10(TestCase):
    """
    1. Create a new DC and cluster with non-default MGMT network
    2. Add a new host to this DC/Cluster
    3. Try to change the MGMT on the setup with the host to be ovirtmgmt
    4. Remove host from cluster
    5. Change MGMT to ovirtmgmt and succeed
    """
    __test__ = True
    bz = {"1250063": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC and a new cluster with non-default MGMT network and
        install a new Host on it
        2. Add ovirtmgmt to setup with the host
        """
        helper.install_host_new_mgmt()
        helper.create_net_dc_cluster(
            dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0,
            net_dict={c.MGMT_BRIDGE: {"required": "true"}}
        )

    @polarion("RHEVM3-6472")
    def test_change_mgmt_net(self):
        """
        1. Try to change the non-default MGMT to the default one, when the Host
        is attached to the Cluster and fail
        2. Return host to its original DC/Cluster
        3. Change MGMT network on Extra Cluster to ovirtmgmt
        4. Check that the change succeeded
        """
        logger.info(
            "Try to change the MGMT %s on %s to be %s and fail as host is "
            "attached to it", c.net1, c.EXTRA_CLUSTER_0, c.MGMT_BRIDGE
        )

        helper.update_mgmt_net(net=c.MGMT_BRIDGE, positive=False)
        helper.check_mgmt_net()

        helper.install_host_new_mgmt(
            network=c.net1, dest_cl=c.CLUSTER_1, new_setup=False
        )

        helper.update_mgmt_net(net=c.MGMT_BRIDGE)
        helper.check_mgmt_net(net=c.MGMT_BRIDGE)

    @classmethod
    def teardown_class(cls):
        """
        Remove extra DC/Cluster
        """
        helper.remove_dc_cluster(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0)


@attr(tier=2)
class TestMGMTNetRole11(TestCase):
    """
    1. Create new cluster when one network exists on the DC and check that this
    network becomes MGMT network
    2. Remove Cluster and then the network from DC
    3. Negative: Try to add a new cluster when there is no network on DC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new DC
        2. Create network on DC
        3. Remove default MGMT network

        """
        helper.create_setup(dc=c.EXT_DC_0, cl=None)
        helper.create_net_dc_cluster(dc=c.EXT_DC_0, cl=None)
        helper.remove_net(net=c.MGMT_BRIDGE, teardown=False)

    @polarion("RHEVM3-6479")
    def test_different_mgmt_net(self):
        """
        1. Add new cluster without providing explicitly MGMT network
        2. Check that the non-default MGMT network exists on that cluster
        3. Remove cluster
        4. Remove non-default MGMT network
        5. Negative: Try to add a new cluster when there is no network on DC
        """
        logger.info("Create a new cluster without explicitly providing MGMT")
        helper.add_cluster(dc=c.EXT_DC_0)
        helper.check_mgmt_net()
        helper.remove_cl()
        helper.remove_net(teardown=False)

        logger.info(
            "Try to create a new cluster when there is no network on DC"
        )
        helper.add_cluster(dc=c.EXT_DC_0, positive=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        helper.remove_dc_cluster(cl=None)
