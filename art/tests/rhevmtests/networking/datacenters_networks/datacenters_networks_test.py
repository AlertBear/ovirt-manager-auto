"""
Testing DataCenter Networks feature.
https://bugzilla.redhat.com/show_bug.cgi?id=741111
2 DC will be created for testing.
In version 3.4 there is new network collection under /api/datacenter.
This test will create/delete/update and list networks under /api/datacenter.
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.networks as ll_networks

logger = logging.getLogger("DC_Networks_Cases")


@unittest_lib.attr(tier=2)
class TestDatacentersNetworksTestCaseBase(unittest_lib.NetworkTest):

    """
    Base class which provides teardown class method for each test case
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        helper.delete_net_in_datacenter()


class TestDataCenterNetworksCase1(TestDatacentersNetworksTestCaseBase):
    """
    List all networks under datacenter.
    """
    __test__ = True
    dc1_net_list = None
    dc2_net_list = None

    @classmethod
    def setup_class(cls):
        """
        Create networks under 2 datacenters.
        """
        cls.dc1_net_list = helper.create_net_in_datacenter(net_num=10)
        cls.dc2_net_list = helper.create_net_in_datacenter(
            dc=conf.DC_NAMES[1], prefix="dc2_net"
        )

    @polarion("RHEVM3-4132")
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        logger.info("Checking that all networks exist in the datacenters")
        engine_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.DC_NAMES[0]
        )
        for net in self.dc1_net_list:
            if net not in [i.name for i in engine_dc_net_list]:
                raise conf.NET_EXCEPTION(
                    "%s was expected to be in %s" % (net, conf.DC_NAMES[0])
                )
        engine_extra_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.DC_NAMES[1]
        )
        for net in self.dc2_net_list:
            if net not in [i.name for i in engine_extra_dc_net_list]:
                raise conf.NET_EXCEPTION(
                    "%s was expected to be in %s" % (net, conf.DC_NAMES[1])
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        helper.delete_net_in_datacenter(dc=conf.DC_NAMES[1])
        super(TestDataCenterNetworksCase1, cls).teardown_class()


class TestDataCenterNetworksCase2(TestDatacentersNetworksTestCaseBase):
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
        for key, val in conf.CREATE_NET_DICT.iteritems():
            name = "_".join([ll_networks.NETWORK_NAME, key])
            kwargs_dict = {
                key: val,
                "name": name
            }
            if not ll_networks.create_network_in_datacenter(
                True, conf.DC_NAMES[0], **kwargs_dict
            ):
                raise conf.NET_EXCEPTION(
                    "Fail to create %s network on %s" % (
                        name, conf.DC_NAMES[0]
                    )
                )

    @polarion("RHEVM3-4135")
    def test_verify_network_parameters(self):
        """
        Verify that all networks have the correct parameters.
        """
        logger.info("Verify that all networks have the correct parameters")
        for key, val in conf.CREATE_NET_DICT.iteritems():
            name = "_".join([ll_networks.NETWORK_NAME, key])
            net_obj = ll_networks.get_network_in_datacenter(
                name, conf.DC_NAMES[0]
            )

            if key == "vlan_id":
                res = net_obj.get_vlan().get_id()

            elif key == "usages":
                res = net_obj.get_usages().get_usage()

            else:
                res = getattr(net_obj, key)

            if res != val:
                raise conf.NET_EXCEPTION(
                    "%s %s should be %s but have %s" % (name, key, val, res)
                )


class TestDataCenterNetworksCase3(TestDatacentersNetworksTestCaseBase):
    """
    Update network under datacenter.
    """
    __test__ = True
    dc1_net_list = None

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        cls.dc1_net_list = helper.create_net_in_datacenter()

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

        logger.info("Update networks under %s", conf.DC_NAMES[0])
        for idx, net in enumerate(self.dc1_net_list):
            key = conf.VERIFY_NET_LIST[idx]
            val = conf.CREATE_NET_DICT[conf.VERIFY_NET_LIST[idx]]
            kwargs_dict = {key: val}
            logger.info("Updating %s %s to %s", net, key, val)
            if not ll_networks.update_network_in_datacenter(
                True, net, conf.DC_NAMES[0], **kwargs_dict
            ):
                raise conf.NET_EXCEPTION(
                    "Fail to update %s %s to %s" % (net, key, val)
                )


class TestDataCenterNetworksCase4(TestDatacentersNetworksTestCaseBase):
    """
    Delete networks under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 networks under datacenter
        """
        helper.create_net_in_datacenter()

    @polarion("RHEVM3-4134")
    def test_delete_networks(self):
        """
        Delete networks under datacenter.
        """
        helper.delete_net_in_datacenter()
