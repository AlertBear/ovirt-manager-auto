#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Display of NIC Slave/Bond fault on RHEV-M Event Log
1 DC, 1 Cluster, 1 Host will be created for testing.
"""

import helper
import logging
import config as c
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, remove_net_from_setup
)

logger = logging.getLogger("Int_Fault_Event_Cases")

HOST_INTERFACE_STATE_UP = c.HOST_INTERFACE_STATE_UP
HOST_INTERFACE_STATE_DOWN = c.HOST_INTERFACE_STATE_DOWN
HOST_BOND_SLAVE_STATE_UP = c.HOST_BOND_SLAVE_STATE_UP
HOST_BOND_SLAVE_STATE_DOWN = c.HOST_BOND_SLAVE_STATE_DOWN
STATE_UP = c.STATE_UP
STATE_DOWN = c.STATE_DOWN


class TestNicFaultTestCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """
    apis = set(["rest"])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        logger.info("Removing all labels from %s interfaces", c.HOST_0)
        if not ll_networks.remove_label(host_nic_dict={c.HOST_0: c.HOST_NICS}):
            logger.error("Couldn't remove labels from Hosts")

        logger.info("Removing all networks from setup")
        if not remove_net_from_setup(
                host=c.VDS_HOSTS_0, auto_nics=[0],
                data_center=c.DC_0, all_net=True,
                mgmt_network=c.MGMT_BRIDGE
        ):
            logger.error("Cannot remove network from setup")

        logger.info("Setting all %s interfaces UP", c.HOST_0)
        for nic in c.HOST_NICS[1:]:
            if not helper.set_nic_up(nic=nic, sleep=False):
                logger.error("Couldn't set up nic %s", nic)


@attr(tier=2)
class TestNicFault01(TestNicFaultTestCaseBase):
    """
    1. Attach label to host interface
    2. ip link set down the host interface
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach label to host interface
        """
        logger.info(
            "Attach label %s to %s on %s", c.LABEL_0, c.HOST_NICS[1], c.HOST_0
        )
        if not ll_networks.add_label(
            label=c.LABEL_0, host_nic_dict={c.HOST_0: [c.HOST_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't add label %s to the Host NIC %s but should" %
                (c.LABEL_0, c.HOST_NICS[1])
            )

    @polarion("RHEVM3-4153")
    def test_label_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


@attr(tier=2)
class TestNicFault02(TestNicFaultTestCaseBase):
    """
    1. Attach required network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach required network to host NIC
        """
        local_dict = {c.NETWORK_0: {"nic": 1}}

        logger.info("Attach %s network to DC/Cluster/Host", c.NETWORK_0)
        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % c.NETWORK_0
            )

    @polarion("RHEVM3-4167")
    def test_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Activating the host if needed")
        if not hl_hosts.activate_host_if_not_up(c.HOST_0):
            logger.error("Failed to activate the host")

        logger.info("Call LabelTestCaseBase teardown")
        super(TestNicFault02, cls).teardown_class()


@attr(tier=2)
class TestNicFault03(TestNicFaultTestCaseBase):
    """
    Check empty NIC failure
    """
    __test__ = True

    @polarion("RHEVM3-4166")
    def test_empty_nic_fault(self):
        """
        Check empty NIC fault
        """
        helper.empty_nic_fault()


@attr(tier=2)
class TestNicFault04(TestNicFaultTestCaseBase):
    """
    1. Attach label to BOND
    2. ifconfig down slave1 of the BOND
    3. ifconfig down slave2 of the BOND
    4. ifconfig up slave1 of the BOND
    5. ifconfig up slave2 of the BOND
    6. ifconfig down the BOND interface
    7. ifconfig up the BOND interface
    """
    __test__ = True
    bz = {"1164533": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach label to BOND
        """
        local_dict1 = {
            None: {
                "nic": c.BOND_0, "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Create Bond %s", c.BOND_0)
        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create bond %s " % c.BOND_0)

        logger.info(
            "Attach label %s to %s on %s", c.LABEL_0,
            c.BOND_0, c.HOST_0
        )
        if not ll_networks.add_label(
            label=c.LABEL_0, host_nic_dict={c.HOST_0: [c.BOND_0]}
        ):
            raise NetworkException(
                "Couldn't add label %s to the Host NIC %s but should" %
                (c.LABEL_0, c.BOND_0)
            )

    @polarion("RHEVM3-4165")
    def test_label_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()


@attr(tier=2)
class TestNicFault05(TestNicFaultTestCaseBase):
    """
    1. Attach required network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = True
    bz = {"1164533": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach required network to BOND
        """
        logger.info("Create and attach network over BOND")
        local_dict = {
            c.NETWORK_0: {
                "nic": c.BOND_0, "slaves": [2, 3]
            }
        }

        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s to bond %s" %
                (c.NETWORK_0, c.BOND_0)
            )

    @polarion("RHEVM3-4164")
    def test_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Activating the host if needed")
        if not hl_hosts.activate_host_if_not_up(c.HOST_0):
            logger.error("Failed to activate the host")

        logger.info("Call LabelTestCaseBase teardown")
        super(TestNicFault05, cls).teardown_class()


@attr(tier=2)
class TestNicFault06(TestNicFaultTestCaseBase):
    """
    1. Create BOND without label or network attached.
    2. ifconfig down slave1 of the BOND
    3. ifconfig down slave2 of the BOND
    4. ifconfig up slave1 of the BOND
    5. ifconfig up slave2 of the BOND
    6. ifconfig down the BOND interface
    7. ifconfig up the BOND interface
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create BOND without network attached to it.
        """
        logger.info("Create BOND")
        local_dict1 = {
            None: {
                "nic": c.BOND_0, "slaves": [2, 3]
            }
        }
        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create bond %s " % c.BOND_0)

    @polarion("RHEVM3-4163")
    def test_empty_bond_fault(self):
        """
        Check empty BOND fault
        """
        helper.empty_bond_fault()


@attr(tier=2)
class TestNicFault07(TestNicFaultTestCaseBase):
    """
    1. Attach non-required network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach non-required network to host NIC
        """
        local_dict = {
            c.NETWORK_0: {
                "nic": 1, "required": "false"
            }
        }

        logger.info("Attach %s network to DC/Cluster/Host", c.NETWORK_0)
        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % c.NETWORK_0
            )

    @polarion("RHEVM3-4162")
    def test_non_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


@attr(tier=2)
class TestNicFault08(TestNicFaultTestCaseBase):
    """
    1. Attach non-required network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = True
    bz = {"1164533": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach non-required network to BOND
        """
        logger.info("Create and attach network over BOND")
        local_dict = {
            c.NETWORK_0: {
                "nic": c.BOND_0, "slaves": [2, 3], "required": "false"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % c.NETWORK_0
            )

    @polarion("RHEVM3-4161")
    def test_non_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()


@attr(tier=2)
class TestNicFault09(TestNicFaultTestCaseBase):
    """
    1. Attach non-vm network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach non-vm network to host NIC
        """
        local_dict = {
            c.NETWORK_0: {
                "nic": 1, "required": "false", "usages": ""
            }
        }

        logger.info("Attach %s network to DC/Cluster/Host", c.NETWORK_0)
        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % c.NETWORK_0
            )

    @polarion("RHEVM3-4160")
    def test_non_required_nic_fault(self):
        """
        Check NIC fault
        """
        helper.nic_fault()


@attr(tier=2)
class TestNicFault10(TestNicFaultTestCaseBase):
    """
    1. Attach non-vm network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = True
    bz = {"1164533": {"engine": None, "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Attach non-vm network to BOND
        """
        logger.info("Create and attach network over BOND")
        local_dict = {
            c.NETWORK_0: {
                "nic": c.BOND_0, "slaves": [2, 3], "required": "false",
                "usages": ""
            }
        }

        if not createAndAttachNetworkSN(
            data_center=c.DC_0, cluster=c.CL_0,
            host=c.VDS_HOSTS_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % c.NETWORK_0
            )

    @polarion("RHEVM3-4159")
    def test_non_required_bond_fault(self):
        """
        Check BOND fault
        """
        helper.bond_fault()
