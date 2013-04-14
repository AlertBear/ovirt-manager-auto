#! /usr/bin/python

from concurrent.futures import ThreadPoolExecutor
from nose.tools import istest
from unittest import TestCase
import logging

from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException
from art.test_handler.settings import opts

import config
from art.test_handler.exceptions import\
    DataCenterException, VMException, NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import\
    addNetwork, addNetworkToCluster
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic,\
    sendSNRequest, genSNBond
from art.rhevm_api.tests_lib.low_level.vms import\
    addNic, getVmNicLinked, getVmNicPlugged, removeNic,\
    updateNic, getVmNicNetwork, startVm, getVmNicPortMirroring
from art.rhevm_api.utils.test_utils import checkMTU

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class Linked_Case1_231692_236620_231710(TestCase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 5 VNICs on VM with different params for plugged/linked
        '''
        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [('true', 'true'), ('true', 'false'),
                                ('false', 'true'), ('false', 'false')]
        for i in range(len(plug_link_param_list)):
            if not addNic(True, config.VM_NAME[0], name='nic'+str(i+2),
                          network=config.VLAN_NETWORKS[i],
                          plugged=plug_link_param_list[i][0],
                          linked=plug_link_param_list[i][1]):
                raise VMException("Cannot add VNIC to VM")
        if not addNic(True, config.VM_NAME[0], name='nic6',
                      network=None,
                      plugged='true',
                      linked='true'):
                raise VMException("Cannot add VNIC to VM")

    @istest
    def checkCombinationPluggedLinkedValues(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4, nic6 is True")
        for nic_name in ('nic2', 'nic4', 'nic6'):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic2, nic3, nic6 is True")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in ('nic3', 'nic5'):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in ('nic4', 'nic5'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside rhevm to unplugged")
        for nic_name in ('nic2', 'nic3', 'nic6'):
            updateNic(True, config.VM_NAME[0], nic_name, plugged=False)
        logger.info("Removing all the VNICs beside rhevm")
        for i in range(5):
            if not removeNic(True, config.VM_NAME[0], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


class Linked_Case2_231698_231697(TestCase):
    """
    Create permutation for the Plugged/Linked VNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 2 VNICs on stopped VM with different nic type for plugged/linked
        '''
        logger.info("Creating VNICs with different nic types for stopped VM")
        if not addNic(True, config.VM_NAME[1], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      interface=config.NIC_TYPE_RTL8139,
                      plugged='true', linked='true'):
                raise VMException("Cannot add VNIC to VM")
        if not addNic(True, config.VM_NAME[1], name='nic3',
                      interface=config.NIC_TYPE_E1000,
                      network=config.VLAN_NETWORKS[1],
                      plugged='true', linked='false'):
                raise VMException("Cannot add VNIC to VM")

    @istest
    def checkCombinationPluggedLinkedValues(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic3 is False" +
                    " and Updating its state to True")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic3'))
        updateNic(True, config.VM_NAME[1], "nic3", linked=True)

        logger.info(" Checking linked state on nic2 is True" +
                    " and Updating its state to False")
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic2'))
        updateNic(True, config.VM_NAME[1], "nic2", linked=False)

        logger.info("Checking that linked state on nics was correctly updated")
        self.assertFalse(getVmNicLinked(config.VM_NAME[1], nic='nic2'))
        self.assertTrue(getVmNicLinked(config.VM_NAME[1], nic='nic3'))

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            updateNic(True, config.VM_NAME[1], nic_name, network=None)

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with its original networks " +
                    "and unplugging them")
        updateNic(True, config.VM_NAME[1], "nic3",
                  network=config.VLAN_NETWORKS[1], plugged=False)
        updateNic(True, config.VM_NAME[1], "nic2",
                  network=config.VLAN_NETWORKS[0], plugged=False)

        logger.info("Testing that update nics with non-empty " +
                    "networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with empty networks")
        for nic_name in ('nic3', 'nic2'):
            updateNic(True, config.VM_NAME[1], nic_name, network=None)

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ('nic3', 'nic2'):
            self.assertFalse(getVmNicNetwork(config.VM_NAME[1], nic=nic_name))

        logger.info("Updating both NICs with its original networks " +
                    "and plugging them")
        for nic_name in ('nic3', 'nic2'):
            updateNic(True, config.VM_NAME[1], nic_name, plugged=True)

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ('nic3', 'nic2'):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[1], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside rhevm to unplugged")
        for nic_name in ('nic3', 'nic2'):
            updateNic(True, config.VM_NAME[1], nic_name, plugged=False)
        logger.info("Removing all the VNICs beside rhevm")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[1], "nic"+str(i+2)):
                raise NetworkException("Cannot remove nic from setup")


class Linked_Case3_231691(TestCase):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create network on DC/Cluster and add it to VM
        '''
        logger.info("Creating network on DC, Cluster")
        if not addNetwork(True, name=config.NETWORKS[0],
                          data_center=config.DC_NAME):
            raise NetworkException("Cannot add network to DC")
        if not addNetworkToCluster(True, network=config.NETWORKS[0],
                                   cluster=config.CLUSTER_NAME,
                                   required='false'):
            raise NetworkException("Cannot add network to Cluster")
        logger.info("Adding network to VM")
        if not addNic(True, config.VM_NAME[1], name='nic6',
                      network=config.NETWORKS[0]):
                raise VMException("Cannot add VNIC to VM")

    @istest
    def checkStartVm(self):
        """
        Try to start VM when there is no network on the host
        """
        logger.info("Try to start VM with network that is not present" +
                    "on the host in the Cluster")
        self.assertTrue(startVm(False, config.VM_NAME[1]))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating all the networks beside rhevm to unplugged")
        updateNic(True, config.VM_NAME[1], "nic6", plugged=False)
        if not removeNic(True, config.VM_NAME[1], "nic6"):
            raise NetworkException("Cannot remove nic from setup")
        if not (removeNetwork(True, network=config.NETWORKS[0],
                              data_center=config.DC_NAME)):
            raise NetworkException("Cannot remove network from DC")


class Linked_Case4_239344(TestCase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create 1 plugged/linked VNIC with port mirroring enabled
        on running VM
        '''
        logger.info("Creating plugged/linked VNIC with port mirroring on sw1")
        if not addNic(True, vm=config.VM_NAME[0], name='nic2',
                      network=config.VLAN_NETWORKS[0],
                      port_mirroring=config.VLAN_NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    def checkPortMirroringNetwork(self):
        """
        Check scenarios for port mirroring network
        """
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))
        logger.info("Try to switch link down ")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  linked=False))
        logger.info("Try to switch port mirroring off")
        self.assertTrue(updateNic(False, config.VM_NAME[0], "nic2",
                                  port_mirroring=None))
        logger.info("Unplug VNIC")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged=False))
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))
        logger.info("Plugging VNIC back")
        self.assertTrue(updateNic(True, config.VM_NAME[0], "nic2",
                                  plugged=True))
        logger.info("Check port mirroring is enabled")
        self.assertTrue(getVmNicPortMirroring(True, config.VM_NAME[0], "nic2"))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        logger.info("Updating the networks beside rhevm to unplugged")
        updateNic(True, config.VM_NAME[0], "nic2", plugged=False)
        logger.info("Removing all the VNICs beside rhevm")
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
