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
class TestHostNetQOSCase02(TestCase):
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
