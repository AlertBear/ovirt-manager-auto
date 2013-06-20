#! /usr/bin/python
from unittest import TestCase
import logging

from nose.tools import istest

from art.rhevm_api.tests_lib.low_level.hosts import genSNNic, \
    sendSNRequest
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.exceptions import NetworkException
from art.test_handler.settings import opts

import config
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeNetFromSetup
from art.rhevm_api.utils.test_utils import checkMTU


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class JumboFrames_Case01_199743(TestCase):
    """
    Test the bridged VM network with MTU 5000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network with MTU 5000 on DC/Cluster/Hosts
        """
        local_dict = {config.NETWORKS[0]: {'mtu': 5000,
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check physical and logical levels for network sw1 with Jumbo frames
        """
        logger.info("Checking logical layer of bridged network sw1 on host %s"
                    % config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))
        logger.info("Checking physical layer of bridged network sw1 on host %s"
                    % config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case02_200156(TestCase):
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
        """
        Create bridgeless tagged networks with MTU on DC/Cluster/Hosts
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'usages': '', 'mtu': 5000,
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'usages': '', 'mtu': 9000,
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTU(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking logical layer of bridgless tagged network "
                    "sw162 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking logical layer of bridgless tagged network "
                    "sw163 ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1],
                                 bridged=False),
                        "MTU on host %s should be 9000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer for bridgless tagged network ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 nic=config.HOST_NICS[1],
                                 bridged=False),
                        "MTU on host %s should be 9000 and it is "
                        "not" % config.HOSTS[0])

        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.VLAN_NETWORKS[0],
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
        logger.info("Checking physical layer for bridgless tagged networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 nic=config.HOST_NICS[1],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case03_197212(TestCase):
    """
    Positive: Creates bridged network over bond on Host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged vlan network with MTU on DC/Cluster/Host over bond
        """

        local_dict = {None: {'nic': 'bond0', 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': 'bond0', 'mtu': 5000,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def bondModeChange(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers on bond")
        logger.info("Checking logical layer of sw162 over bond")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond0',
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer of sw162 over bond ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Changing the bond mode to mode4")
        rc, out = genSNNic(nic='bond0',
                           network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]],
                           mode=4)

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
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond0',
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot create and attach network")

########################################################################

########################################################################


class JumboFrames_Case04_197214_213_742(TestCase):
    """
    Positive: Creates 2 bridged vlan network and check the network files.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged vlan networks with MTU on DC/Cluster/Host
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'mtu': 5000,
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'mtu': 9000,
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def checkMTUValue(self):
        """
        Check physical and logical levels for bridged vlan networks
        """
        logger.info("Checking physical and logical layers on interfaces")
        logger.info("Checking logical layer of bridgless tagged network sw162")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0]),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking logical layer of bridgless tagged network sw163")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1]),
                        "MTU on host %s should be 9000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer for bridgless tagged networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=9000,
                                 nic=config.HOST_NICS[1]),
                        "MTU on host %s should be 9000 and it is "
                        "not" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case05_199741(TestCase):
    """
    Positive: Creates bridged vlan network over bond on host
              Checks that increasing bond's size doesn't effect
              the parameters in ifcfg- and sys files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts over bond
        """
        local_dict = {None: {'nic': 'bond0', 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': 'bond0',
                                                'mtu': 5000,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    def increasingBondNics(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """

        logger.info("Checking physical and logical layers on bond")
        logger.info("Checking logical layer of sw162 over bond")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond0',
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer of sw162 over bond ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])

        logger.info("Changing the bond to consist of 3 NICs")
        rc, out = genSNNic(nic='bond0', network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[1], config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate network object")

        sendSNRequest(positive=True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0]],
                      check_connectivity='true',
                      connectivity_timeout=60, force='false')

        logger.info("Checking layers after increasing the number "
                    "of bond's nics")
        logger.info("Checking logical layer after increasing the "
                    "number of bond's nics")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond='bond0',
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])
        logger.info("Checking physical layer after extending the "
                    "number of bond's nics")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=5000,
                                 bond='bond0',
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be 5000 and it is "
                        "not" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case06_199787(TestCase):
    """
    Negative: 1. creates bond0 and attach vlan network with MTU 9000 to it.
              2. attaches non_vm network with MTU 5000 to bond0.
    """
    __test__ = True

    local_dict = {None: {'nic': 'bond0', 'mode': 1,
                         'slaves': [config.HOST_NICS[2],
                                    config.HOST_NICS[3]]},
                  config.VLAN_NETWORKS[0]: {'nic': 'bond0',
                                            'mtu': 9000,
                                            'vlan_id': config.VLAN_ID[0],
                                            'required': 'false'},
                  config.NETWORKS[0]: {'nic': 'bond0',
                                       'mtu': 5000,
                                       'usages': '',
                                       'required': 'false'}}

    @classmethod
    def setup_class(cls):
        """
        creates bond0 and attach network sw162 with MTU 9000 to it.
        """

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=cls.local_dict):
            raise NetworkException("Cannot create and attach network")

    @istest
    def NegAddNetworksWithDifferentMTU(self):
        """
        Trying to add two networks with different MTU to the
        same interface - should fail
        """

        logger.info("Negative: Trying to add two networks with "
                    "different MTU to the same interface")
        net_obj = []
        for net, net_param in self.local_dict.items():
            address_list = net_param.get('address', [])
            netmask_list = net_param.get('netmask', [])
            gateway_list = net_param.get('gateway', [])

            rc, out = genSNNic(nic=net_param['nic'],
                               network=net,
                               slaves=net_param.get('slaves', None),
                               mode=net_param.get('mode', None),
                               boot_protocol=net_param.get('bootproto', None),
                               address=address_list.pop(0)
                               if address_list else None,
                               netmask=netmask_list.pop(0)
                               if netmask_list else None,
                               gateway=gateway_list.pop(0)
                               if gateway_list else None)

            if not rc:
                logger.error("Cannot generate network object")
                return False
            net_obj.append(out['host_nic'])

        logger.info("Sending SN request to host %s" % config.HOSTS[0])
        if not sendSNRequest(positive=False,
                             host=config.HOSTS[0],
                             nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            logger.error("Adding two networks with different MTU was "
                         "successful - Should have failed")
            return True
        return False

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")
