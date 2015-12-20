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
import rhevmtests.networking.helper as networking_helper


logger = logging.getLogger("Bridgeless_Networks_Cases")


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################

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
