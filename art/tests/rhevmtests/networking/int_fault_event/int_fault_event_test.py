#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Display of NIC Slave/Bond fault on RHEV-M Event Log
1 DC, 1 Cluster, 1 Host will be created for testing.
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr

from art.unittest_lib import NetworkTest
from art.test_handler.tools import polarion
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Int_Fault_Event_Cases")

HOST_INTERFACE_STATE_UP = conf.HOST_INTERFACE_STATE_UP
HOST_INTERFACE_STATE_DOWN = conf.HOST_INTERFACE_STATE_DOWN
HOST_BOND_SLAVE_STATE_UP = conf.HOST_BOND_SLAVE_STATE_UP
HOST_BOND_SLAVE_STATE_DOWN = conf.HOST_BOND_SLAVE_STATE_DOWN
STATE_UP = conf.STATE_UP
STATE_DOWN = conf.STATE_DOWN


@attr(tier=2)
class TestNicFaultTestCaseBase(NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    apis = set(["rest"])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        hl_hosts.activate_host_if_not_up(conf.HOST_0)
        hl_host_network.clean_host_interfaces(host_name=conf.HOST_0)
        for nic in conf.HOST_NICS[1:]:
            helper.set_nic_up(nic=nic)


class TestNicFault01(TestNicFaultTestCaseBase):
    """
    1. Attach label to host interface
    2. ip link set down the host interface
    3. ip link set up the host NIC
    """
    __test__ = False
    label = conf.LABEL_NAME[1][0]

    @classmethod
    def setup_class(cls):
        """
        Attach label to host interface
        """
        if not ll_networks.add_label(
            label=cls.label, host_nic_dict={
                conf.HOST_0: [conf.HOST_NICS[1]]
            }
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4153")
    def test_label_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


class TestNicFault02(TestNicFaultTestCaseBase):
    """
    1. Attach required network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = False
    net = conf.NETS[2][0]

    @classmethod
    def setup_class(cls):
        """
        Attach required network to host NIC
        """
        local_dict = {
            cls.net: {
                "nic": 1
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4167")
    def test_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


class TestNicFault03(TestNicFaultTestCaseBase):
    """
    1. Attach label to BOND
    2. ifconfig down slave1 of the BOND
    3. ifconfig down slave2 of the BOND
    4. ifconfig up slave1 of the BOND
    5. ifconfig up slave2 of the BOND
    6. ifconfig down the BOND interface
    7. ifconfig up the BOND interface
    """
    __test__ = False
    label = conf.LABEL_NAME[3][0]

    @classmethod
    def setup_class(cls):
        """
        Attach label to BOND
        """
        local_dict1 = {
            None: {
                "nic": conf.BOND_0,
                "slaves": [2, 3],
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_label(
            label=cls.label, host_nic_dict={
                conf.HOST_0: [conf.BOND_0]
            }
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4165")
    def test_label_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()


class TestNicFault04(TestNicFaultTestCaseBase):
    """
    1. Attach required network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = False
    net = conf.NETS[4][0]

    @classmethod
    def setup_class(cls):
        """
        Attach required network to BOND
        """
        local_dict = {
            cls.net: {
                "nic": conf.BOND_0,
                "slaves": [2, 3]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4164")
    def test_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()


class TestNicFault05(TestNicFaultTestCaseBase):
    """
    1. Attach non-required network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = False
    net = conf.NETS[5][0]

    @classmethod
    def setup_class(cls):
        """
        Attach non-required network to host NIC
        """
        local_dict = {
            cls.net: {
                "nic": 1,
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4162")
    def test_non_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


class TestNicFault06(TestNicFaultTestCaseBase):
    """
    1. Attach non-required network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = False
    net = conf.NETS[6][0]

    @classmethod
    def setup_class(cls):
        """
        Attach non-required network to BOND
        """
        local_dict = {
            cls.net: {
                "nic": conf.BOND_0,
                "slaves": [2, 3],
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4161")
    def test_non_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()


class TestNicFault07(TestNicFaultTestCaseBase):
    """
    1. Attach non-vm network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = False
    net = conf.NETS[7][0]

    @classmethod
    def setup_class(cls):
        """
        Attach non-vm network to host NIC
        """
        local_dict = {
            cls.net: {
                "nic": 1,
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4160")
    def test_non_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


class TestNicFault8(TestNicFaultTestCaseBase):
    """
    1. Attach non-vm network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = False
    net = conf.NETS[8][0]

    @classmethod
    def setup_class(cls):
        """
        Attach non-vm network to BOND
        """
        local_dict = {
            cls.net: {
                "nic": conf.BOND_0,
                "slaves": [2, 3],
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4159")
    def test_non_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()
