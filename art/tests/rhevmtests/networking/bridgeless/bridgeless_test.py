#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

import helper
import logging
import config as conf
from art import unittest_lib
import rhevmtests.networking as networking
import rhevmtests.networking.helper as networking_helper


logger = logging.getLogger("Bridgeless_Networks_Cases")


def setup_module():
    """
    running cleanup
    Obtain host NICs for the first Network Host
    Create dummy interfaces
    Create networks
    """
    networking.network_cleanup()
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST0_NICS = conf.VDS_HOSTS[0].nics
    networking_helper.prepare_dummies(
        host_resource=conf.VDS_HOSTS[0], num_dummy=conf.NUM_DUMMYS
    )
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.NET_DICT, dc=conf.DC_NAME[0],
        cluster=conf.CLUSTER_NAME[0]
    )


def teardown_module():
    """
    Cleans the environment
    """
    networking_helper.remove_networks_from_setup(hosts=conf.HOST_0_NAME)
    networking_helper.delete_dummies(host_resource=conf.VDS_HOSTS[0])


@unittest_lib.attr(tier=2)
class TestBridgelessTestCaseBase(unittest_lib.NetworkTest):

    """
    Base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        networking_helper.remove_networks_from_host()


class TestBridgelessCase1(TestBridgelessTestCaseBase):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    def test_bridgeless_network(self):
        """
         Attach Non-VM network to host NIC
        """
        helper.create_networks_on_host(
            nic=conf.HOST0_NICS[1], net=conf.NETS[1][0]
        )


class TestBridgelessCase2(TestBridgelessTestCaseBase):
    """
    Attach Non-VM with VLAN network to host NIC
    """
    __test__ = True

    def test_vlan_bridgeless_network(self):
        """
        Attach Non-VM with VLAN network to host NIC
        """
        helper.create_networks_on_host(
            nic=conf.HOST0_NICS[1], net=conf.NETS[2][0]
        )


class TestBridgelessCase3(TestBridgelessTestCaseBase):
    """
    Create BOND
    Attach Non-VM network with VLAN over BOND
    """
    __test__ = True
    bond = "bond03"

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """

        helper.create_networks_on_host(nic=cls.bond, slaves=conf.DUMMYS[:2])

    def test_bond_bridgeless_network(self):
        """
        Attach Non-VM network with VLAN over BOND
        """
        helper.create_networks_on_host(net=conf.NETS[3][0], nic=self.bond)


class TestBridgelessCase4(TestBridgelessTestCaseBase):
    """
    Create BOND
    Attach Non-VM network over BOND
    """
    __test__ = True
    bond = "bond04"

    @classmethod
    def setup_class(cls):
        """
        Create BOND
        """
        helper.create_networks_on_host(nic=cls.bond, slaves=conf.DUMMYS[2:4])

    def test_bond_bridgeless_network(self):
        """
        Attach bridgeless network over BOND
        """
        helper.create_networks_on_host(net=conf.NETS[4][0], nic=self.bond)
