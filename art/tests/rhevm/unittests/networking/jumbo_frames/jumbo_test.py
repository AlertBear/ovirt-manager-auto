#! /usr/bin/python

from concurrent.futures import ThreadPoolExecutor
from nose.tools import istest
from unittest import TestCase
import logging

from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException
from art.test_handler.settings import opts

import config
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic,\
    sendSNRequest, genSNBond
from art.rhevm_api.utils.test_utils import checkMTU

#import pdb
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class JumboFrames_Case1_199743(TestCase):
    """
    Test the bridged VM network with MTU 5000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network with MTU 5000 on DC/Cluster/Hosts
        '''
        local_dict = {config.NETWORKS[0]: {'mtu': 5000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check physical and logical levels for network sw1 with Jumbo frames
        """
        logger.info("Checking logical layer of bridged network sw1")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))
        logger.info("Checking physical layer of bridged network sw1")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################
class JumboFrames_Case2_200156(TestCase):
    """
    Positive: 1) Creates 2 Non_VM networks with Jumbo Frames
              2) Checks the correct MTU values in the sys/config
                 and sys/class/net
              files
              3) Removes one of the networks
              4) Check the correct values for the MTU in files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create bridgeless networks with MTU on DC/Cluster/Hosts
        '''
        local_dict = {config.NETWORKS[0]: {'vlan_id': config.VLAN_ID[1],
                                           'usages': '', 'mtu': 5000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'},
                      config.NETWORKS[1]: {'vlan_id': config.VLAN_ID[2],
                                           'usages': '', 'mtu': 9000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers for Jumbo ")
        logger.info("Checking logical layer of bridgless network sw1 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1],
                                 bridged=False))
        logger.info("Checking logical layer of bridgless network sw2 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 physical_layer=False,
                                 network=config.NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[2],
                                 bridged=False))
        logger.info("Checking physical layer for bridgless networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 nic=config.HOST_NICS[1],
                                 bridged=False))

        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           vlan=config.VLAN_ID[0])
        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0],
                                 config.HOST_NICS[1]],
                      check_connectivity='true',
                      connectivity_timeout=60,
                      force='false')
        logger.info("Checking physical layer for bridgless networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                        password=config.HOSTS_PW, mtu=5000,
                        nic=config.HOST_NICS[1],
                        bridged=False))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup
        '''
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################
class JumboFrames_Case3_197212(TestCase):
    """
    Positive: Creates bridged network over bond on Host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create bridged networks with MTU on DC/Cluster/Hosts over bond
        '''
        local_dict = {config.NETWORKS[0]: {'bond': 'bond0',
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'mode': 1, 'mtu': 5000,
                                           'vlan_id': config.VLAN_ID[0],
                                           'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def bondModeChange(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers for Jumbo bond ")
        logger.info("Checking logical layer of sw1 over bond")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 bond='bond0',
                                 bridged=False))
        logger.info("Checking physical layer of sw1 over bond ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False))
        logger.info("Changing the bond mode to  mode4")
        rc, out = genSNBond(name='bond0', network=config.NETWORKS[0],
                            slaves=[config.HOST_NICS[2],
                                    config.HOST_NICS[3]], mode=4)

        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(positive=True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0]],
                      check_connectivity='true',
                      connectivity_timeout=60, force='false')
        logger.info("Checking layers after bond mode change")
        logger.info("Checking logical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 bond='bond0',
                                 bridged=False))
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3], bridged=False))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup
        '''
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot create and attach network")

########################################################################

########################################################################


class JumboFrames_Case4_197214_213_742(TestCase):
    """
    Positive: Creates 2 bridged vlan network and check the network files.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create bridged networks with MTU on DC/Cluster/Hosts
        '''
        local_dict = {config.NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                           'mtu': 5000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'},
                      config.NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                           'mtu': 9000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTUValue(self):
        """
        Check physical and logical levels for bridged vlan networks
        """
        logger.info("Checking physical and logical layers for Jumbo ")
        logger.info("Checking logical layer of bridgless network sw1 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0]))
        logger.info("Checking logical layer of bridgless network sw2 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 physical_layer=False,
                                 network=config.NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1]))
        logger.info("Checking physical layer for bridgless networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup
        '''
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")
