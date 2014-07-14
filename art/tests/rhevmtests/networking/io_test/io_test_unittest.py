
"""
Testing Input/Output feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Positive and negative cases for creating/editing networks
with valid/invalid names, IPs, netmask, VLAN, usages.
"""
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms
import logging
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeAllNetworks
from art.rhevm_api.tests_lib.low_level.networks import \
    addNetwork, addNetworkToCluster, updateNetwork, createNetworkInDataCenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from rhevmtests import config


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class IOTestCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not removeAllNetworks(config.DC_NAME[0]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class Test01(IOTestCaseBase):
    """
    Positive: Creating & adding networks with valid names to the cluster
    Negative: Trying to create networks with invalid names
    """
    __test__ = True

    @istest
    @tcms(14499, 390936)
    def check_network_names(self):
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
                                       data_center=config.DC_NAME[0]),
                            "The network %s was not created although "
                            "it should have" % networkName)

            logger.info("Trying to add %s to cluster %s",
                        networkName, config.CLUSTER_NAME[0])
            self.assertTrue(addNetworkToCluster(
                positive=True, network=networkName,
                cluster=config.CLUSTER_NAME[0]), "Cannot add network %s to "
                                                 "Cluster" % networkName)

        for networkName in invalid_names:
            logger.info("Trying to create networks with the name %s - should"
                        " fail", networkName)
            self.assertFalse(addNetwork(positive=True,
                                        name=networkName,
                                        data_center=config.DC_NAME[0]),
                             "The network %s was created although "
                             "it shouldn't have" % networkName)


@attr(tier=1)
class Test02(IOTestCaseBase):
    """
    Negative: Trying to create networks with invalid IPs
    """
    __test__ = True

    @istest
    @tcms(14499, 390938)
    def check_invalid_ips(self):
        """
        Negative: Trying to create networks with invalid IPs
        (Creation should fail)
        """
        invalid_ips = [["1.1.1.260"],
                       ["1.1.260.1"],
                       ["1.260.1.1"],
                       ["260.1.1.1"],
                       ["1.2.3"],
                       ["1.1.1.X"]]

        for invalid_ip in invalid_ips:
            logger.info("Trying to create a network with invalid IP %s",
                        invalid_ip)

            local_dict = {'invalid_ips': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'address': invalid_ip,
                                          'netmask': ['255.255.255.0'],
                                          'required': 'false'}}

            self.assertFalse(
                createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                         cluster=config.CLUSTER_NAME[0],
                                         host=config.HOSTS[0],
                                         network_dict=local_dict,
                                         auto_nics=[config.HOST_NICS[0]]),
                "Network with invalid IP (%s) was created" % invalid_ip)


@attr(tier=1)
class Test03(IOTestCaseBase):
    """
    Negative: Trying to create networks with invalid netmask
    """
    __test__ = True

    @istest
    @tcms(14499, 390940)
    def check_invalid_netmask(self):
        """
        Negative: Trying to create networks with invalid netmask
        """
        invalid_netmasks = [["255.255.255.260"],
                            ["255.255.260.0"],
                            ["255.260.255.0"],
                            ["260.255.255.0"],
                            ["255.255.255."],
                            ["255.255.255.X"]]

        for invalid_netmask in invalid_netmasks:
            logger.info("Trying to create a network with netmask %s",
                        invalid_netmask)

            local_dict = {'invalid_netmask': {'nic': config.HOST_NICS[1],
                                              'bootproto': 'static',
                                              'address': ['1.1.1.1'],
                                              'netmask': invalid_netmask,
                                              'required': 'false'}}

            self.assertFalse(
                createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                         cluster=config.CLUSTER_NAME[0],
                                         host=config.HOSTS[0],
                                         network_dict=local_dict,
                                         auto_nics=[config.HOST_NICS[0]]),
                "Network invalid_netmask with invalid ip (%s) was created"
                % invalid_netmask)


@attr(tier=1)
class Test04(IOTestCaseBase):
    """
    Negative: Trying to create a network with netmask but without an ip address
    """
    __test__ = True

    @istest
    @tcms(14499, 390942)
    def check_netmask_without_ip(self):
        """
        Negative: Trying to create a network with netmask but without an
        IP address
        """
        logger.info("Trying to create a network with netmask but"
                    " without ip address")
        local_dict = {'netmaskWithNoIP': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'netmask': ['255.255.255.0'],
                                          'required': 'false'}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                     cluster=config.CLUSTER_NAME[0],
                                     host=config.HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[config.HOST_NICS[0]]),
            "Network without ip was created although it shouldn't have")


@attr(tier=1)
class Test05(IOTestCaseBase):
    """
    Negative: Trying to create a network with static ip but without
    netmask
    """
    __test__ = True

    @istest
    @tcms(14499, 393107)
    def check_static_ip_without_netmask(self):
        """
        Negative: Trying to create a network with static IP but without netmask
        """
        logger.info("Trying to create a network with static ip but"
                    " without netmask")
        local_dict = {'ipWithNoNetmask': {'nic': config.HOST_NICS[1],
                                          'bootproto': 'static',
                                          'address': ['1.1.1.1'],
                                          'required': 'false'}}
        self.assertFalse(
            createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                     cluster=config.CLUSTER_NAME[0],
                                     host=config.HOSTS[0],
                                     network_dict=local_dict,
                                     auto_nics=[config.HOST_NICS[0]]),
            "Network without netmask was created although it shouldn't"
            " have")


@attr(tier=1)
class Test06(IOTestCaseBase):
    """
    Positive: Creating networks with valid MTU and adding them to a cluster.
    Negative: Trying to create a network with invalid MTUs - should fail.
    """
    __test__ = True

    @istest
    @tcms(14499, 390944)
    def check_mtu(self):
        """
        Positive: Creating networks with valid MTUs and adding them to a
        cluster.
        Negative: Trying to create a network with invalid MTUs - should fail.
        """
        # as per #BZ 1010663, upper capping for MTU was removed, rising tested
        # MTUs

        valid_mtus = [68, 69, 8999, 9000, 65520, 2147483647]
        invalid_mtus = [-5, 67, 2147483648]
        for index_1, invalid_mtu in enumerate(invalid_mtus):
            logger.info("Trying to create networks with mtu = %s"
                        " - Should fail.", invalid_mtu)
            self.assertFalse(addNetwork(positive=True,
                                        name='invalid_mtu%s' % index_1,
                                        mtu=invalid_mtu,
                                        data_center=config.DC_NAME[0]),
                             "Network with mtu = %s was created "
                             "although it shouldn't have" % invalid_mtu)

        for index_2, valid_mtu in enumerate(valid_mtus):
            logger.info("Creating networks with mtu = %s", valid_mtu)
            self.assertTrue(addNetwork(positive=True,
                                       name='valid_mtu%s' % index_2,
                                       mtu=valid_mtu,
                                       data_center=config.DC_NAME[0]),
                            "Network with mtu = %s was not created" % valid_mtu
                            )

            logger.info("Adding valid_mtu%s to cluster %s",
                        index_2, config.CLUSTER_NAME[0])
            self.assertTrue(
                addNetworkToCluster(positive=True, network='valid_mtu%s' %
                                                           index_2,
                                    cluster=config.CLUSTER_NAME[0]),
                "Cannot add network valid_mtu%s to Cluster" % index_2)


@attr(tier=1)
class Test07(IOTestCaseBase):
    """
    Negative: Trying to create a network with invalid usages value
    """
    __test__ = True

    @istest
    @tcms(14499, 390946)
    def check_invalid_usages(self):
        """
        Trying to create a network with invalid usages value
        """
        usages = 'Unknown'
        logger.info("Trying to create network with usages = %s", usages)
        self.assertFalse(addNetwork(positive=True,
                                    name='invalid_usage',
                                    usages=usages,
                                    data_center=config.DC_NAME[0]),
                         "Network with usages = %s was created" % usages)


@attr(tier=1)
class Test08(IOTestCaseBase):
    """
    Positive: Creating networks with valid VLAN IDs & adding them to a cluster.
    Negative: Trying to create networks with invalid VLAN IDs.
    """
    __test__ = True

    @istest
    @tcms(14499, 390948)
    def check_vlan_ids(self):
        """
        Positive: Creating networks with valid VLAN IDs & adding them to a
        cluster.
        Negative: Trying to create networks with invalid VLAN IDs.
        """
        valid_vlan_ids = [4094, 1111, 111, 11, 1, 0]
        invalid_vlan_ids = [-10, 4095, 4096]
        for invalid_index, vlan_id in enumerate(invalid_vlan_ids):
            logger.info("Trying to create network with vlan id = %s - should "
                        "fail", vlan_id)
            if addNetwork(positive=True,
                          name='invalid_vlan_id%s' % invalid_index,
                          vlan_id=vlan_id,
                          data_center=config.DC_NAME[0]):
                raise NetworkException("Network with VLAN id = %s was created"
                                       " although it shouldn't have "
                                       "(Valid range = [0,4094])" % vlan_id)

        for valid_index, vlan_id in enumerate(valid_vlan_ids):
            logger.info("Creating network with vlan id = %s",
                        vlan_id)
            if not addNetwork(positive=True,
                              name='valid_vlan_id%s' % valid_index,
                              vlan_id=vlan_id,
                              data_center=config.DC_NAME[0]):
                raise NetworkException("Network with VLAN ID %s was not "
                                       "created although it should have"
                                       % vlan_id)

            logger.info("Adding valid VLAN ID %s to cluster %s",
                        vlan_id, config.CLUSTER_NAME[0])
            if not addNetworkToCluster(positive=True,
                                       network='valid_vlan_id%s' % valid_index,
                                       cluster=config.CLUSTER_NAME[0]):
                raise NetworkException("Cannot add network %s to Cluster %s" %
                                       vlan_id, config.CLUSTER_NAME[0])


class Test09(IOTestCaseBase):
    """
    Positive: Create network and edit its name to valid name
    Negative: Try to edit its name to invalid name
    """
    initial_name = "NET_default"

    __test__ = True

    @classmethod
    def setup_class(cls, initial_name=initial_name):
        """
        Create network in data center with valid name and description
        """
        kwargs_dict = {"name": initial_name,
                       "description": "network with initial valid name"}

        logger.info("Creating network %s on data center %s",
                    initial_name, config.DC_NAME[0])
        if not createNetworkInDataCenter(True, config.DC_NAME[0],
                                         **kwargs_dict):
            raise NetworkException("Failed to create %s network on %s" %
                                   (initial_name, config.DC_NAME[0]))

    @istest
    @tcms(14499, 390950)
    def edit_network_name(self, initial_name=initial_name):
        """
        Positive: Should succeed editing network to valid name
        Negative: Should fail to edit networks with invalid names
        """

        valid_name = "NET_changed"
        invalid_name = "inv@lidName"

        logger.info("Trying to change name of network %s to %s - should"
                    "succeed", initial_name, valid_name)
        self.assertTrue(updateNetwork(positive=True,
                                      network=initial_name,
                                      name=valid_name,
                                      description="network with changed name"),
                        ("Failed to change the name of network %s to %s" % (
                            initial_name, valid_name)))

        logger.info("Trying to change name of network %s to %s - should fail",
                    valid_name, invalid_name)
        self.assertFalse(updateNetwork(positive=True,
                                       network=valid_name,
                                       name=invalid_name),
                         ("Changed the name of network %s to %s - should fail"
                          % (valid_name, invalid_name)))


@attr(tier=1)
class Test10(IOTestCaseBase):
    """
    Positive: change network VLAN tag to valid VLAN tag
    Negative: change network VLAN tag to invalid VLAN tag
    """
    __test__ = True

    default_name = "NET_edit_tag"

    @classmethod
    def setup_class(cls, default_name=default_name):
        """
        Create network in the data center with valid name and description
        """
        kwargs_dict = {"name": default_name,
                       "description": "initial network with valid name "
                                      "without VLAN ID"}

        logger.info("Creating network %s on data center %s", default_name,
                    config.DC_NAME[0])

        if not createNetworkInDataCenter(True, config.DC_NAME[0],
                                         **kwargs_dict):
            raise NetworkException("Failed to create %s network on %s" %
                                   (default_name, config.DC_NAME[0]))

    @istest
    @tcms(14499, 390952)
    def edit_network_tag(self, default_name=default_name):
        """
        Positive: Should succeed editing network to valid VLAN tags
        Negative: Should fail to edit networks with invalid VLAN tags
        """
        valid_tags = [0, 1, 15, 444, 4094]
        invalid_tags = [-1, 4099]

        for valid_tag in valid_tags:
            logger.info("Trying to change VLAN tag of network %s to %s - "
                        "should succeed", default_name, valid_tag)
            self.assertTrue(updateNetwork(positive=True,
                                          network=default_name,
                                          vlan_id=valid_tag),
                            ("Failed to change VLAN tag of network %s to %s" %
                             (default_name, valid_tag)))

        for invalid_tag in invalid_tags:
            logger.info("Trying to change VLAN tag of network %s to %s - "
                        "should fail", default_name, invalid_tag)
            self.assertFalse(updateNetwork(positive=True,
                                           network=default_name,
                                           vlan_id=invalid_tag),
                             ("Changed the VLAN tag of network %s to %s -"
                              " should fail" % (default_name, invalid_tag)))


@attr(tier=1)
class Test11(IOTestCaseBase):
    """
    Positive: Change VM network to be non-VM network
    Positive: Change non-VM network to be VM network
    """
    __test__ = True

    default_name = "VM_network"

    @classmethod
    def setup_class(cls, default_name=default_name):
        """
        Create network in the  Data center with valid name and valid
        description
        """
        kwargs_dict = {"name": default_name, "description": 'VM network'}

        logger.info("Creating VM network %s on data center %s",
                    default_name, config.DC_NAME[0])

        if not createNetworkInDataCenter(True, config.DC_NAME[0],
                                         **kwargs_dict):
            raise NetworkException("Failed to create %s network in DC %s" %
                                   (default_name, config.DC_NAME[0]))

    @istest
    @tcms(14499, 390954)
    def edit_vm_network(self, default_name=default_name):
        """
        Positive: Should succeed changing VM network to non-VM network
        """
        logger.info("Trying to change VM network %s to nonVM network - should "
                    "succeed", default_name)
        self.assertTrue(updateNetwork(positive=True,
                                      network=default_name,
                                      usages="",
                                      description="nonVM network"),
                        ("Failed to change network %s to nonVM network" %
                         default_name))

        logger.info("Trying to change nonVM network %s back to be VM network "
                    "- should succeed", default_name)
        self.assertTrue(updateNetwork(positive=True,
                                      network=default_name,
                                      usages='vm',
                                      description="VM network again"),
                        ("Failed to change network %s to VM network" %
                         default_name))
