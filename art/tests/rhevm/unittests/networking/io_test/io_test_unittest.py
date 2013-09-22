
#! /usr/bin/python
from nose.tools import istest
from unittest import TestCase
import logging
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeAllNetworks
from art.rhevm_api.tests_lib.low_level.networks import \
    addNetwork, addNetworkToCluster
from art.test_handler.exceptions import NetworkException
import config

from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class Test01_checkNetworkNames(TestCase):
    """
    Positive: Creating & adding networks with valid names to the cluster
    Negative: Trying to create networks with invalid names
    """
    __test__ = True

    @istest
    def checkNetworkNames(self):
        """
        Positive: Should succeed creating networks with valid names
        Negative: Should fail to create networks with invalid names
        """
        valid_names = ['endsWithNumber1',
                       'nameMaxLengthhh',
                       '1startsWithNumb',
                       '1a2s3d4f5g6h',
                       '01234567891011',
                       '______']
        invalid_names = ['networkWithMoreThanFifteenChars',
                         'inv@lidName',
                         '________________',
                         'bond',
                         '']

        for networkName in valid_names:

            logger.info("Trying to create networks with the name %s",
                        networkName)
            self.assertTrue(addNetwork(positive=True,
                                       name=networkName,
                                       data_center=config.DC_NAME),
                            "The network %s was not created although "
                            "it should have" % networkName)

            logger.info("Trying to add %s to cluster %s",
                        networkName, config.CLUSTER_NAME)
            self.assertTrue(addNetworkToCluster(positive=True,
                                                network=networkName,
                                                cluster=config.CLUSTER_NAME),
                            "Cannot add network %s to Cluster" % networkName)

        for networkName in invalid_names:
            logger.info("Trying to create networks with the name %s - should"
                        "fail", networkName)
            self.assertFalse(addNetwork(positive=True,
                                        name=networkName,
                                        data_center=config.DC_NAME),
                             "The network %s was created although "
                             "it shouldn't have" % networkName)

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting teardown")
        if not removeAllNetworks(config.DC_NAME):
            raise NetworkException("Cannot remove network from setup")


class Test02_checkInvalidIPs(TestCase):
    """
    Negative: Trying to create networks with invalid IPs
    """
    __test__ = True

    @istest
    def checkInvalidIPs(self):
        """
        Negative: Trying to create networks with invalid IPs
        (Creation should fail)
        """
        invalid_ips = [["1.1.1.260"],
                       ["1.1.260.1"],
                       ["1.260.1.1"],
                       ["260.1.1.1"]]

        for i in range(4):
            logger.info("Trying to create a network with invalid ip %s",
                        invalid_ips[i])

            local_dict = {'invalid_ips': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'address': invalid_ips[i],
                                          'netmask': ['255.255.255.0'],
                                          'required': 'false'}}

            self.assertFalse(
                createAndAttachNetworkSN(data_center=config.DC_NAME,
                                         cluster=config.CLUSTER_NAME,
                                         host=config.HOSTS[0],
                                         network_dict=local_dict,
                                         auto_nics=[config.HOST_NICS[0]]),
                "Network with invalid ip (%s) was created" % invalid_ips[i])


class Test03_checkInvalidNetmask(TestCase):
    """
    Negative: Trying to create networks with invalid netmasks
    """
    __test__ = True

    @istest
    def checkInvalidNetmask(self):
        """
        Negative: Trying to create networks with invalid netmasks
        """
        invalid_netmasks = [["255.255.255.260"],
                            ["255.255.260.0"],
                            ["255.260.255.0"],
                            ["260.255.255.0"]]

        for i in range(4):
            logger.info("Trying to create a network with netmask %s",
                        invalid_netmasks[i])

            local_dict = {'invalid_netmask': {'nic': config.HOST_NICS[1],
                                              'bootproto': 'static',
                                              'address': ['1.1.1.1'],
                                              'netmask': invalid_netmasks[i],
                                              'required': 'false'}}

            self.assertFalse(
                createAndAttachNetworkSN(data_center=config.DC_NAME,
                                         cluster=config.CLUSTER_NAME,
                                         host=config.HOSTS[0],
                                         network_dict=local_dict,
                                         auto_nics=[config.HOST_NICS[0]]),
                "Network invalid_netmask with invalid ip (%s) was created"
                % invalid_netmasks[i])


class Test04_checkNetmaskWithoutIp(TestCase):
    """
    Negative: Trying to create a network with netmask but without an
    ip address
    """
    __test__ = True

    @istest
    def checkNetmaskWithoutIp(self):
        """
        Negative: Trying to create a network with netmask but without an
        ip address
        """
        logger.info("Trying to create a network with netmask but"
                    " without ip address")
        local_dict = {'netmaskWithNoIP': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'netmask': ['255.255.255.0'],
                                          'required': 'false'}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=config.DC_NAME,
                                     cluster=config.CLUSTER_NAME,
                                     host=config.HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[config.HOST_NICS[0]]),
            "Network without ip was created although it shouldn't have")

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting teardown")
        if not removeAllNetworks(config.DC_NAME):
            raise NetworkException("Cannot remove network from setup")


class Test05_checkStaticIpWithoutNetmask(TestCase):
    """
    Negative: Trying to create a network with static ip but without
    netmask
    """
    __test__ = True

    @istest
    def checkStaticIpWithoutNetmask(self):
        """
        Negative: Trying to create a network with static ip but without
        netmask
        """
        logger.info("Trying to create a network with static ip but"
                    " without netmask")
        local_dict = {'ipWithNoNetmask': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'address': ['1.1.1.1'],
                                          'required': 'false'}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=config.DC_NAME,
                                     cluster=config.CLUSTER_NAME,
                                     host=config.HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[config.HOST_NICS[0]]),
            "Network without netmask was created although it shouldn't"
            " have")

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown")
        if not removeAllNetworks(config.DC_NAME):
            raise NetworkException("Cannot remove network from setup")


class Test06_checkMTU(TestCase):
    """
    Positive: Creating networks with valid MTU and adding them
              to a cluster.
    Negative: Trying to create a network with invalid MTUs - should
              fail.
    """
    __test__ = True

    @istest
    def checkMTU(self):
        """
        Positive: Creating networks with valid MTU add adding them
                  to a cluster.
        Negative: Trying to create a networks with invalid MTUs
        """
        valid_mtus = [68, 69, 8999, 9000]
        invalid_mtus = [-5, 9001, 67]
        for valid_index, mtu in enumerate(invalid_mtus):
            logger.info("Trying to create networks with mtu = %s"
                        " - Should fail.", mtu)
            self.assertFalse(addNetwork(positive=True,
                                        name='invalid_mtu%s' % valid_index,
                                        mtu=mtu,
                                        data_center=config.DC_NAME),
                             "Network with mtu = %s was created "
                             "although it shouldn't have" % mtu)

        for invalid_index, mtu in enumerate(valid_mtus):
            logger.info("Creating networks with mtu = %s", mtu)
            self.assertTrue(addNetwork(positive=True,
                                       name='valid_mtu%s' % invalid_index,
                                       mtu=mtu,
                                       data_center=config.DC_NAME),
                            "Network with mtu = %s was not created" % mtu)

            logger.info("Adding valid_mtu%s to cluster %s",
                        invalid_index, config.CLUSTER_NAME)
            self.assertTrue(addNetworkToCluster(positive=True,
                                                network='valid_mtu%s'
                                                        % invalid_index,
                                                cluster=config.CLUSTER_NAME),
                            "Cannot add network valid_mtu%s to Cluster"
                            % invalid_index)

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown")
        if not removeAllNetworks(config.DC_NAME):
            raise NetworkException("Cannot remove network from setup")


class Test07_checkInvalidUsages(TestCase):
    """
    Negative: Trying to create a network with invalid usages value
    """
    __test__ = True

    @istest
    def checkInvalidUsages(self):
        """
        Trying to create a network with invalid usages value
        """
        usages = 'Unknown'
        logger.info("Trying to create network with usages = %s", usages)
        self.assertFalse(addNetwork(positive=True,
                                    name='invalid_usage',
                                    usages=usages,
                                    data_center=config.DC_NAME),
                         "Network with usages = %s was created" % usages)


class Test08_checkVlanIDs(TestCase):
    """
    Positive: Creating networks with valid IDs & adding them to a cluster.
    Negative: Trying to create networks with invalid vlan IDs.
    """
    __test__ = True

    @istest
    def checkVlanIDs(self):
        """
        Positive: Creating networks with valid IDs & adding them to a cluster.
        Negative: Trying to create networks with invalid vlan IDs.
        """
        valid_vlan_id = [4094, 111, 0]
        invalid_vlan_ids = [-10, 4095, 4096]
        for invalid_index, vlan_id in enumerate(invalid_vlan_ids):
            logger.info("Trying to create network with vlan id = %s",
                        vlan_id)
            if addNetwork(positive=True,
                          name='invalid_vlan_id%s' % invalid_index,
                          vlan_id=vlan_id,
                          data_center=config.DC_NAME):
                logger.error(
                    "Network with vlan id = %s was created although"
                    " it shouldn't have (Valid range = [0,4094])", vlan_id)
                return False

        for valid_index, vlan_id in enumerate(valid_vlan_id):
            logger.info("Creating network with vlan id = %s",
                        vlan_id)
            if not addNetwork(positive=True,
                              name='valid_vlan_id%s' % valid_index,
                              vlan_id=vlan_id,
                              data_center=config.DC_NAME):
                logger.error(
                    "Network with vlan id = %s was not created although "
                    "it should have", vlan_id)
                return False

            logger.info("Adding valid_vlan_id%s to cluster %s",
                        valid_index, config.CLUSTER_NAME)
            if not addNetworkToCluster(positive=True,
                                       network='valid_vlan_id%s' % valid_index,
                                       cluster=config.CLUSTER_NAME):
                logger.error("Cannot add network %s to Cluster",
                             ('valid_vlan_id%s' % valid_index))
                return False

    @classmethod
    def teardown_class(cls):
        '''
        Remove networks from the setup.
        '''
        logger.info("Starting the teardown")
        if not removeAllNetworks(config.DC_NAME):
            raise NetworkException("Cannot remove network from setup")
