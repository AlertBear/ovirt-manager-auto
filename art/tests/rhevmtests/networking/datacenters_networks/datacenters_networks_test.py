"""
Testing DataCenter Networks feature.
https://bugzilla.redhat.com/show_bug.cgi?id=741111
2 DC will be created for testing.
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import logging
from rhevmtests.networking import config
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.networks import \
    getNetworksInDataCenter, getNetworkInDataCenter, \
    createNetworkInDataCenter, updateNetworkInDataCenter, \
    createNetworksInDataCenter, deleteNetworksInDataCenter, NETWORK_NAME

LOGGER = logging.getLogger(__name__)
CREATE_NET_DICT = {"description": "New network", "stp": True,
                   "vlan_id": 500, "usages": [],
                   "mtu": 5555}
VERIFY_NET_LIST = ["description", "stp", "vlan_id", "usages", "mtu"]

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=0)
class DataCenterNetworksCase1(TestCase):
    """
    List all networks under datacenter.
    """
    __test__ = True
    net_list = None

    @classmethod
    def setup_class(cls):
        """
        Create networks under 2 datacenters.
        """
        LOGGER.info("Create 10 networks under %s", config.DC_NAME[0])
        cls.net_list = []
        nets = createNetworksInDataCenter(config.DC_NAME[0], 10)
        if not nets:
            raise NetworkException("Fail to create 10 network on %s" %
                                   config.DC_NAME[0])
        cls.net_list.extend(nets)

        LOGGER.info("Create 5 networks under %s", config.DC_NAME[1])
        if not createNetworksInDataCenter(config.DC_NAME[1], 5):
            raise NetworkException("Fail to create 5 network on %s" %
                                   config.DC_NAME[1])

    @istest
    @tcms(12098, 333370)
    def get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        LOGGER.info("Checking that all networks are exist in the datacenter")
        for net in getNetworksInDataCenter(config.DC_NAME[0]):
            net_name = net.get_name()
            if net_name == config.MGMT_BRIDGE:
                continue
            if net_name not in self.net_list:
                raise NetworkException("%s was expected to be in %s" %
                                       (net_name, config.DC_NAME[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        for dc_name in (config.DC_NAME[0], config.DC_NAME[1]):
            LOGGER.info("Remove all networks from %s", dc_name)
            if not deleteNetworksInDataCenter(dc_name, config.MGMT_BRIDGE):
                raise NetworkException("Fail to delete all networks from DC")


@attr(tier=0)
class DataCenterNetworksCase2(TestCase):
    """
    Create network under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create networks under datacenter with:
        description
        stp
        vlan_id
        usages
        mtu
        """
        for key, val in CREATE_NET_DICT.iteritems():
            name = "_".join([NETWORK_NAME, key])
            kwargs_dict = {key: val, "name": name}
            if not createNetworkInDataCenter(True, config.DC_NAME[0],
                                             **kwargs_dict):
                raise NetworkException("Fail to create %s network on %s" %
                                       (name, config.DC_NAME[0]))

    @istest
    @tcms(12098, 333360)
    def verify_network_parameters(self):
        """
        Verify that all networks have the correct parameters.
        """
        LOGGER.info("Verify that all networks have the correct parameters")
        for key, val in CREATE_NET_DICT.iteritems():
            name = "_".join([NETWORK_NAME, key])
            net_obj = getNetworkInDataCenter(name, config.DC_NAME[0])

            if key == "vlan_id":
                res = net_obj.get_vlan().get_id()

            elif key == "usages":
                res = net_obj.get_usages().get_usage()

            else:
                res = getattr(net_obj, key)

            if res != val:
                raise NetworkException("%s %s should be %s but have %s" %
                                       (name, key, val, res))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        LOGGER.info("Remove all networks from DC")
        if not deleteNetworksInDataCenter(config.DC_NAME[0],
                                          config.MGMT_BRIDGE):
            raise NetworkException("Fail to delete all networks from DC")


@attr(tier=0)
class DataCenterNetworksCase3(TestCase):
    """
    Update network under datacenter.
    """
    __test__ = True
    net_list = None

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        LOGGER.info("Create 5 networks under %s", config.DC_NAME[0])
        cls.net_list = []
        nets = createNetworksInDataCenter(config.DC_NAME[0], 5)
        if not nets:
            raise NetworkException("Fail to create 5 network on %s" %
                                   config.DC_NAME[0])
        cls.net_list.extend(nets)

    @istest
    @tcms(12098, 333363)
    def update_networks_parameters(self):
        """
        Update network under datacenter with:
        description
        stp
        vlan_id
        usages
        mtu
        """
        LOGGER.info("Update networks under %s", config.DC_NAME[0])
        for idx, net in enumerate(self.net_list):
            key = VERIFY_NET_LIST[idx]
            val = CREATE_NET_DICT[VERIFY_NET_LIST[idx]]
            kwargs_dict = {key: val}
            LOGGER.info("Updating %s %s to %s", net, key, val)
            if not updateNetworkInDataCenter(True, net, config.DC_NAME[0],
                                             **kwargs_dict):
                raise NetworkException("Fail to update %s %s to %s" %
                                       (net, key, val))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        LOGGER.info("Remove all networks from DC")
        if not deleteNetworksInDataCenter(config.DC_NAME[0],
                                          config.MGMT_BRIDGE):
            raise NetworkException("Fail to delete all networks from DC")


@attr(tier=0)
class DataCenterNetworksCase4(TestCase):
    """
    Delete networks under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        LOGGER.info("Create 5 networks under %s", config.DC_NAME[0])
        if not createNetworksInDataCenter(config.DC_NAME[0], 5):
            raise NetworkException("Fail to create 5 network on %s" %
                                   config.DC_NAME[0])

    @istest
    @tcms(12098, 333361)
    def delete_networks(self):
        """
        Delete networks under datacenter.
        """
        LOGGER.info("Remove all networks from DC")
        if not deleteNetworksInDataCenter(config.DC_NAME[0],
                                          config.MGMT_BRIDGE):
            raise NetworkException("Fail to delete all networks from DC")

    @classmethod
    def teardown_class(cls):
        """
        No need for teardown as the test deletes all the networks.
        """
        LOGGER.info("No need for teardown as the test deletes the networks")
