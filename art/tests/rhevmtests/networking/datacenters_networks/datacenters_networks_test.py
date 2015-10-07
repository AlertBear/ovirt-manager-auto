"""
Testing DataCenter Networks feature.
https://bugzilla.redhat.com/show_bug.cgi?id=741111
2 DC will be created for testing.
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import logging
from rhevmtests.networking import config
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.networks import(
    get_networks_in_datacenter, get_network_in_datacenter,
    create_network_in_datacenter, update_network_in_datacenter,
    create_networks_in_datacenter, delete_networks_in_datacenter, NETWORK_NAME
)

logger = logging.getLogger("DC_Networks_Cases")
CREATE_NET_DICT = {"description": "New network", "stp": True,
                   "vlan_id": 500, "usages": [],
                   "mtu": 5555}
VERIFY_NET_LIST = ["description", "stp", "vlan_id", "usages", "mtu"]
DC_NAMES = [config.DC_NAME[0], "DC_NET_DC2"]

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
class TestDataCenterNetworksCase1(TestCase):
    """
    List all networks under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create networks under 2 datacenters.
        """
        logger.info("Create 10 networks under %s", DC_NAMES[0])
        if not create_networks_in_datacenter(DC_NAMES[0], 10, "dc1_net"):
            raise NetworkException(
                "Fail to create 10 network on %s" % DC_NAMES[0]
            )
        logger.info("Create 5 networks under %s", DC_NAMES[1])
        if not create_networks_in_datacenter(DC_NAMES[1], 5, "dc2_net"):
            raise NetworkException(
                "Fail to create 5 network on %s" % DC_NAMES[1]
            )

    @polarion("RHEVM3-4132")
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        logger.info("Checking that all networks exist in the datacenters")
        dc1_net_list = ["_".join(["dc1_net", str(i)]) for i in xrange(10)]
        engine_dc_net_list = get_networks_in_datacenter(DC_NAMES[0])
        for net in dc1_net_list:
            if net not in [i.name for i in engine_dc_net_list]:
                raise NetworkException(
                    "%s was expected to be in %s" % (net, DC_NAMES[0])
                )
        dc2_net_list = ["_".join(["dc2_net", str(i)]) for i in xrange(5)]
        engine_extra_dc_net_list = get_networks_in_datacenter(DC_NAMES[1])
        for net in dc2_net_list:
            if net not in [i.name for i in engine_extra_dc_net_list]:
                raise NetworkException(
                    "%s was expected to be in %s" % (net, DC_NAMES[1])
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        for dc_name in DC_NAMES:
            logger.info("Remove all networks from %s", dc_name)
            if not delete_networks_in_datacenter(dc_name, config.MGMT_BRIDGE):
                logger.error("Fail to delete all networks from DC")


@attr(tier=2)
class TestDataCenterNetworksCase2(TestCase):
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
            if not create_network_in_datacenter(
                True, DC_NAMES[0], **kwargs_dict
            ):
                raise NetworkException(
                    "Fail to create %s network on %s" % (name, DC_NAMES[0])
                )

    @polarion("RHEVM3-4135")
    def test_verify_network_parameters(self):
        """
        Verify that all networks have the correct parameters.
        """
        logger.info("Verify that all networks have the correct parameters")
        for key, val in CREATE_NET_DICT.iteritems():
            name = "_".join([NETWORK_NAME, key])
            net_obj = get_network_in_datacenter(name, DC_NAMES[0])

            if key == "vlan_id":
                res = net_obj.get_vlan().get_id()

            elif key == "usages":
                res = net_obj.get_usages().get_usage()

            else:
                res = getattr(net_obj, key)

            if res != val:
                raise NetworkException(
                    "%s %s should be %s but have %s" % (name, key, val, res)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove all networks from DC")
        if not delete_networks_in_datacenter(
            DC_NAMES[0], config.MGMT_BRIDGE
        ):
            logger.error("Fail to delete all networks from DC")


@attr(tier=2)
class TestDataCenterNetworksCase3(TestCase):
    """
    Update network under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        logger.info("Create 5 networks under %s", DC_NAMES[0])
        cls.net_list = []
        if not create_networks_in_datacenter(DC_NAMES[0], 5, "dc1_net"):
            raise NetworkException(
                "Fail to create 5 network on %s" % DC_NAMES[0]
            )

    @polarion("RHEVM3-4133")
    def test_update_networks_parameters(self):
        """
        Update network under datacenter with:
        description
        stp
        vlan_id
        usages
        mtu
        """
        dc1_net_list = ["_".join(["dc1_net", str(i)]) for i in xrange(5)]
        logger.info("Update networks under %s", DC_NAMES[0])
        for idx, net in enumerate(dc1_net_list):
            key = VERIFY_NET_LIST[idx]
            val = CREATE_NET_DICT[VERIFY_NET_LIST[idx]]
            kwargs_dict = {key: val}
            logger.info("Updating %s %s to %s", net, key, val)
            if not update_network_in_datacenter(
                True, net, DC_NAMES[0], **kwargs_dict
            ):
                raise NetworkException(
                    "Fail to update %s %s to %s" % (net, key, val)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove all networks from DC")
        if not delete_networks_in_datacenter(
            DC_NAMES[0], config.MGMT_BRIDGE
        ):
            logger.error("Fail to delete all networks from DC")


@attr(tier=2)
class TestDataCenterNetworksCase4(TestCase):
    """
    Delete networks under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        logger.info("Create 5 networks under %s", DC_NAMES[0])
        if not create_networks_in_datacenter(DC_NAMES[0], 5, "dc1_net"):
            raise NetworkException(
                "Fail to create 5 network on %s" % DC_NAMES[0]
            )

    @polarion("RHEVM3-4134")
    def test_delete_networks(self):
        """
        Delete networks under datacenter.
        """
        logger.info("Remove all networks from DC")
        if not delete_networks_in_datacenter(
            DC_NAMES[0], config.MGMT_BRIDGE
        ):
            raise NetworkException("Fail to delete all networks from DC")
