#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""
import logging

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as conf
import helper
from _pytest_art.marks import tier2
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr

logger = logging.getLogger("Required_Network_Cases")


@tier2
@attr(tier=2)
class TearDownRequiredNetwork(NetworkTest):
    """
    Teardown class for RequiredNetwork job
    """
    net = None

    @classmethod
    def teardown_class(cls):
        """
        Set host NICs up if needed
        Remove network from setup
        """
        for nic in conf.HOST_0_NICS[1:]:
            if not ll_hosts.check_host_nic_status(
                host_resource=conf.VDS_0_HOST, nic=nic,
                status=conf.NIC_STATE_UP
            ):
                logger.info("Set %s up", nic)
                if not conf.VDS_0_HOST.network.if_up(nic=nic):
                    logger.error("Failed to set %s up", nic)

        if cls.net:
            hl_networks.remove_net_from_setup(
                host=conf.HOST_0_NAME, data_center=conf.DC_0, network=[cls.net]
            )

        hl_hosts.activate_host_if_not_up(host=conf.HOST_0_NAME)


class TestRequiredNetwork01(TearDownRequiredNetwork):
    """
    Check that management network is required by default
    Try to set it to non required.
    """
    __test__ = True
    cluster = conf.CL_0
    mgmt = conf.MGMT_BRIDGE

    @polarion("RHEVM3-3753")
    def test_mgmt(self):
        """
        Check that management network is required by default
        Try to set it to non required.
        """
        if not ll_networks.is_network_required(
            network=self.mgmt, cluster=self.cluster
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.mgmt,
            required="false"
        ):
            raise conf.NET_EXCEPTION()


class TestRequiredNetwork02(TearDownRequiredNetwork):
    """
    Attach required non-VM network to host
    Set host NIC down
    Check that host is non-operational
    """
    __test__ = True
    net = conf.NETS[2][0]
    networks = [net]

    @classmethod
    def setup_class(cls):
        """
        Attach required non-VM network to host
        """
        local_dict = {
            cls.net: {
                "nic": 1,
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3744")
    def test_nonoperational(self):
        """
        Set host NIC down
        Check that host is non-operational
        """
        helper.set_nics_and_wait_for_host_status(
            nics=[conf.HOST_0_NICS[1]], nic_status=conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )


class TestRequiredNetwork03(TearDownRequiredNetwork):
    """
    Attach required VLAN network over BOND.
    Set BOND slaves down
    Check that host is non-operational
    Set BOND slaves up
    Check that host is operational
    """
    __test__ = True
    net = conf.NETS[3][0]
    bond = "bond4"
    vlan = conf.VLAN_IDS[0]

    @classmethod
    def setup_class(cls):
        """
        Attach required network over BOND.
        """
        local_dict = {
            None: {
                "nic": cls.bond,
                "slaves": [2, 3]
            },
            cls.net: {
                "nic": cls.bond,
                "vlan_id": cls.vlan
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3752")
    def test_1_nonoperational_bond_down(self):
        """
        Set bond SLAVES DOWN
        Check that host is non-operational
        """
        helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4], nic_status=conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )

    @polarion("RHEVM3-3745")
    def test_2_nonoperational_bond_down(self):
        """
        Set BOND slaves up
        Check that host is operational
        """
        helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4], nic_status=conf.NIC_STATE_UP,
        )
