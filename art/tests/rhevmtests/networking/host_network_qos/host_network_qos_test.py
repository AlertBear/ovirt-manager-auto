#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network host QoS feature.
Create, update and remove tests will be done for network host QoS feature
"""
import helper
import logging
import config as conf
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Network_VNIC_QoS_Tests")

QOS_NAME = ("HostQoSProfile1", "HostQoSProfile2")
HOST_NET_QOS_TYPE = "hostnetwork"

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class TestHostNetworkQoSTestCaseBase(TestCase):
    """
    Base class which provides teardown class method for each test case
    that inherits this class
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the host NICs.
        """
        logger.info("Removing all networks from %s", conf.HOST_1)
        if not hl_host_network.clean_host_interfaces(conf.HOST_1):
            logger.error(
                "Failed to remove all networks from %s", conf.HOST_1
            )


@attr(tier=2)
class TestHostNetQOSCase01(TestCase):
    """
    Add new network QOS (named)
    """
    __test__ = True
    bz = {"1274187": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @polarion("RHEVM3-6525")
    def test_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Fill in weighted share only for this QoS
        3) Fill in all 3 values for this QoS:
        a) weighted share, b) rate limit, c) commited rate
        4) Update the provided values
        """
        helper.create_host_net_qos(outbound_average_linkshare=conf.TEST_VALUE)

        logger.info(
            "Update existing Host Network QoS profile under DC by adding rate "
            "limit and committed rate"
        )
        helper.update_host_net_qos(
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE
        )
        logger.info(
            "Update weighted share, limit and committed rate for existing QoS"
        )
        helper.update_host_net_qos(
            outbound_average_linkshare=conf.TEST_VALUE + 1,
            outbound_average_upperlimit=conf.TEST_VALUE + 1,
            outbound_average_realtime=conf.TEST_VALUE + 1
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        helper.remove_qos_from_dc()


@attr(tier=2)
class TestHostNetQOSCase02(TestHostNetworkQoSTestCaseBase):
    """
    Attach network with QoS to host NIC
    """
    __test__ = True
    net = conf.NETS[2][0]

    @polarion("RHEVM3-6526")
    def test_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": "hostnetwork",
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_realtime": conf.TEST_VALUE,
                        "outbound_average_upperlimit": conf.TEST_VALUE
                        }
                }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            self.net, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" % (
                    self.net, conf.HOST_1_NICS[1], conf.HOST_1
                )
            )


@attr(tier=2)
class TestHostNetQOSCase03(TestHostNetworkQoSTestCaseBase):
    """
    Increase default Engine limitation for QoS and test that weighted share
    and rate configuration work well with new Engine configuration

    """
    __test__ = True
    net = conf.NETS[3][0]

    @classmethod
    def setup_class(cls):
        """
        Attach network to Host NIC
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_1_NICS[1],
                    }
            }
        }
        logger.info(
            "Attaching %s to %s on %s",
            cls.net, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (cls.net, conf.HOST_1_NICS[1], conf.HOST_1)
            )

    @polarion("RHEVM3-6527")
    def test_weight_share_rate_new_limit(self):
        """
        Update network on host NIC with QoS weighted share parameters
        """

        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": "hostnetwork",
                        "outbound_average_linkshare": conf.DEFAULT_SHARE + 5,
                        "outbound_average_upperlimit": conf.DEFAULT_RATE + 1,
                        "outbound_average_realtime": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        logger.info(
            "Configure weighted share and rate limit on Engine to the value "
            "of %s and %s appropriately",
            conf.UPDATED_SHARE, conf.UPDATED_SHARE
        )
        cmd1 = "=".join([conf.QOS_SHARE, conf.UPDATED_SHARE])
        if not conf.test_utils.set_engine_properties(
            conf.ENGINE, [cmd1], restart=False
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update the weighted share to the value of %s" %
                conf.UPDATED_SHARE
            )

        cmd2 = "=".join([conf.RATE_LIMIT, conf.UPDATED_RATE])
        if not conf.test_utils.set_engine_properties(conf.ENGINE, [cmd2]):
            raise conf.NET_EXCEPTION(
                "Couldn't update the rate to the value of %s" %
                conf.UPDATED_RATE
            )

        logger.info(
            "Configuring %s on %s to have weighted share and rate limit to be "
            "above their original default values", self.net, conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to configure %s to have share and rate limit be above "
                "original default values" % self.net
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        Update engine to have default value for the weighted share
        and rate limit
        """
        super(TestHostNetQOSCase03, cls).teardown_class()

        logger.info(
            "Update weighted share and rate limit to the default values "
            "on engine"
        )
        cmd1 = "=".join([conf.QOS_SHARE, str(conf.DEFAULT_SHARE)])
        if not conf.test_utils.set_engine_properties(
            conf.ENGINE, [cmd1], restart=False
        ):
            logger.error(
                "Couldn't update the weighted share to the default value"
            )
        cmd2 = "=".join([conf.RATE_LIMIT, str(conf.DEFAULT_RATE)])
        if not conf.test_utils.set_engine_properties(conf.ENGINE, [cmd2]):
            logger.error(
                "Couldn't update the rate to the default value"
            )


@attr(tier=2)
class TestHostNetQOSCase04(TestHostNetworkQoSTestCaseBase):
    """
    Test weighted share and rate limitation
    """
    __test__ = True
    net1 = conf.NETS[4][0]
    bz = {"1271220": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        1) Attach network to the host
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net1,
                    "nic": conf.HOST_1_NICS[1],
                    },
            }
        }

        logger.info(
            "Attaching %s to %s on %s",
            cls.net1, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s" %
                (cls.net1, conf.HOST_1_NICS[1], conf.HOST_1)
            )

    @polarion("RHEVM3-6528")
    def test_rate_share_limit(self):
        """
        Negative: Try to update networks on host NIC with:
        1)QoS rate limit beyond configured maximum
        2)QoS committed rate beyond configured maximum
        3) weighted share beyond configured maximum
        """

        host_qos_dict_1 = {
            "update": {
                "1": {
                    "network": self.net1,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": "hostnetwork",
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_upperlimit": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        host_qos_dict_2 = {
            "update": {
                "2": {
                    "network": self.net1,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": "hostnetwork",
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_realtime": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        host_qos_dict_3 = {
            "update": {
                "3": {
                    "network": self.net1,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": "hostnetwork",
                        "outbound_average_linkshare": conf.DEFAULT_SHARE + 1,
                    }
                }
            }
        }

        for net_dict in (
            host_qos_dict_1, host_qos_dict_2, host_qos_dict_3
        ):
            logger.info(
                "Negative: Try updating %s on %s with %s ",
                self.net1, conf.HOST_1, net_dict
            )
            if hl_host_network.setup_networks(
                host_name=conf.HOST_1, **net_dict
            ):
                raise conf.NET_EXCEPTION(
                    "Succeeded to update %s with %s" % (self.net1, net_dict)
                )


@attr(tier=2)
class TestHostNetQOSCase05(TestCase):
    """
    Add new network QOS (named) with
    1) committed rate value higher than rate limit and fail
    2) committed rate value lower than rate limit and succeed
    """
    __test__ = True

    @polarion("RHEVM3-6532")
    def test_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Negative: Try to configure committed rate higher than rate limit
        3) Configure committed rate lower than rate limit
        """
        logger.info(
            "Negative: Try to create new Network QoS profile under DC"
            "with committed rate value higher than rate limit value"
        )
        helper.create_host_net_qos(
            positive=False,
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE + 2
        )

        logger.info(
            "Create new Network QoS profile under DC with committed rate "
            "value lower than rate limit value"
        )
        helper.create_host_net_qos(
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE - 2
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        helper.remove_qos_from_dc()
