#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network host QoS feature.
Create, update and remove tests will be done for network host QoS feature
"""
import logging
import helper
import config as conf
from art.unittest_lib import attr
import rhevmtests.networking.helper as net_helper
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import polarion, bz as bzd  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network


logger = logging.getLogger("Network_Host_QoS_Tests")
MB_CONVERTER = 1000000


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
    bz = {"1274187": {"engine": None, "version": ["3.6"]}}
    qos_name = conf.QOS_NAME[0]

    @polarion("RHEVM3-6525")
    def test_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Fill in weighted share only for this QoS
        3) Fill in all 3 values for this QoS:
        a) weighted share, b) rate limit, c) commited rate
        4) Update the provided values
        """
        net_helper.create_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.TEST_VALUE
        )

        logger.info(
            "Update existing Host Network QoS profile under DC by adding rate "
            "limit and committed rate"
        )
        net_helper.update_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE
        )
        logger.info(
            "Update weighted share, limit and committed rate for existing QoS"
        )
        net_helper.update_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.TEST_VALUE + 1,
            outbound_average_upperlimit=conf.TEST_VALUE + 1,
            outbound_average_realtime=conf.TEST_VALUE + 1
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        net_helper.remove_qos_from_dc(qos_name=cls.qos_name)


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
                        "type_": conf.HOST_NET_QOS_TYPE,
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
                        "type_": conf.HOST_NET_QOS_TYPE,
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
                        "type_": conf.HOST_NET_QOS_TYPE,
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
                        "type_": conf.HOST_NET_QOS_TYPE,
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
                        "type_": conf.HOST_NET_QOS_TYPE,
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
    qos_name = conf.QOS_NAME[1]

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
        net_helper.create_host_net_qos(
            qos_name=self.qos_name,
            positive=False,
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE + 2
        )

        logger.info(
            "Create new Network QoS profile under DC with committed rate "
            "value lower than rate limit value"
        )
        net_helper.create_host_net_qos(
            qos_name=self.qos_name,
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE - 2
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove Host Network QoS
        """
        net_helper.remove_qos_from_dc(qos_name=cls.qos_name)


@attr(tier=2)
class TestHostNetQOSCase06(TestHostNetworkQoSTestCaseBase):
    """
    1) Negative: Try to have network with and without QoS configured on the
    same NIC and fail
    2) Positive: Update network without QoS with QoS and succeed to have both
    networks on the same NIC with setupNetwork command
    """
    __test__ = True
    net1 = conf.NETS[6][0]
    net2 = conf.NETS[6][1]
    qos_name = conf.QOS_NAME[2]

    @classmethod
    def setup_class(cls):
        """
        1) Create new Host Network QoS profile under DC and attach this QoS
        to the first network on DC (when second network is without QoS)
        """

        net_helper.create_host_net_qos(
            qos_name=cls.qos_name,
            outbound_average_linkshare=conf.TEST_VALUE,
        )

        ll_networks.update_network_in_datacenter(
            positive=True, network=cls.net1, datacenter=conf.DC_NAME,
            qos_dict={
                "qos_name": cls.qos_name,
                "datacenter": conf.DC_NAME
            }
        )

    @polarion("RHEVM3-6533")
    def test_add_network_qos(self):
        """
        1) Negative: Try to attach both networks to the Host
        2) Attach QoS to the second network and succeed to attach both
        networks to the Host
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net1,
                    "nic": conf.HOST_1_NICS[1],
                    },
                "2": {
                    "network": self.net2,
                    "nic": conf.HOST_1_NICS[1],
                    },
                }
        }

        logger.info(
            "Negative: Trying to attach %s and %s to %s on %s",
            self.net1, self.net2, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Succeeded to attach %s and %s to %s on %s when shouldn't" %
                (self.net1, self.net2, conf.HOST_1_NICS[1], conf.HOST_1)
            )

        if not ll_networks.update_network_in_datacenter(
            positive=True, network=self.net2, datacenter=conf.DC_NAME,
            qos_dict={
                "qos_name": self.qos_name,
                "datacenter": conf.DC_NAME
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s to have host Network QoS" % self.net2
            )
        logger.info(
            "Attach %s and %s to %s on %s",
            self.net1, self.net2, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s and %s to %s on %s when should" %
                (self.net1, self.net2, conf.HOST_1_NICS[1], conf.HOST_1)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the host
        Remove Host Network QoS
        """
        super(TestHostNetQOSCase06, cls).teardown_class()
        net_helper.remove_qos_from_dc(qos_name=cls.qos_name)


@attr(tier=2)
class TestHostNetQOSCase07(TestHostNetworkQoSTestCaseBase):
    """
    Remove host network QoS that is attached to the Network on the Host
    """
    __test__ = True
    net1 = conf.NETS[7][0]
    qos_name = conf.QOS_NAME[3]

    @classmethod
    def setup_class(cls):
        """
        1) Create new Host Network QoS profile under DC and attach this QoS
        to the network on DC
        2) Attach this network to the Host
        """
        logger.info(
            "Create Network QoS profile under DC"
        )
        net_helper.create_host_net_qos(
            qos_name=cls.qos_name,
            positive=True, outbound_average_linkshare=conf.TEST_VALUE,
        )

        if not ll_networks.update_network_in_datacenter(
            positive=True, network=cls.net1, datacenter=conf.DC_NAME,
            qos_dict={
                "qos_name": cls.qos_name,
                "datacenter": conf.DC_NAME
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s to have Host Network QoS" % cls.net1
            )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net1,
                    "nic": conf.HOST_1_NICS[1],
                    },
                }
        }

        logger.info(
            "Attach %s to %s on %s",
            cls.net1, conf.HOST_1_NICS[1], conf.HOST_1
        )
        if not hl_host_network.setup_networks(
            host_name=conf.HOST_1, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s on %s " %
                (cls.net1, conf.HOST_1_NICS[1], conf.HOST_1)
            )

    @polarion("RHEVM3-6537")
    def test_remove_network_qos(self):
        """
        1) Remove host network QoS that is attached to the network on host
        2) Check that the network is unsynced
        3) Sync the network
        """
        net_helper.remove_qos_from_dc(qos_name=self.qos_name)
        logger.info("Check the network is unsynced")
        if net_helper.networks_sync_status(
            host=conf.HOST_1, networks=[self.net1]
        ):
            raise conf.NET_EXCEPTION(
                "%s should be unsynced, but it's not" % self.net1
            )

        logger.info("Sync the network")
        net_helper.sync_networks(host=conf.HOST_1, networks=[self.net1])


@attr(tier=2)
class TestHostNetQOSCase08(TestHostNetworkQoSTestCaseBase):
    """
    1) Create QoS while creating a new network
    2) Update another network with the QoS from previous step
    """
    __test__ = True
    net1 = conf.NETS[8][0]
    net2 = conf.NETS[8][1]
    qos_name = conf.QOS_NAME[4]

    @polarion("RHEVM3-6535")
    def test_01_create_qos_when_add_network(self):
        """
        Create QoS when creating a new network on the setup
        """
        if not ll_networks.addNetwork(
            True, name=self.net1, data_center=conf.DC_NAME,
            qos_dict={
                "datacenter": conf.DC_NAME,
                "qos_name": self.qos_name,
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add %s when creating QoS %s to %s" %
                (self.net1, self.qos_name, conf.DC_NAME)
            )

    @polarion("RHEVM3-14276")
    def test_02_update_network_with_qos(self):
        """
        Update existing network on the setup with the QoS from test01
        """
        logger.info("Update another network with the %s", self.qos_name)
        if not ll_networks.update_network_in_datacenter(
            positive=True, network=self.net2, datacenter=conf.DC_NAME,
            qos_dict={
                "qos_name": self.qos_name,
                "datacenter": conf.DC_NAME
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s to have host Network QoS" % self.net2
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the host
        Remove Host Network QoS
        """
        net_helper.remove_qos_from_dc(qos_name=cls.qos_name)


@attr(tier=2)
class TestHostNetQOSCase09(TestHostNetworkQoSTestCaseBase):
    """
    1) Create QoS while updating existing network
    2) Create another QoS when editing the same network
    3) Update the network with unlimited QoS
    """
    __test__ = True
    net1 = conf.NETS[9][0]
    qos_name1 = conf.QOS_NAME[5]
    qos_name2 = conf.QOS_NAME[6]

    @polarion("RHEVM3-6536")
    def test_01_create_qos_when_update_network(self):
        """
        1) Create QoS when editing a network on the setup
        2) Create another QoS when editing the same network
        3) Update the network with unlimited QoS
        """
        logger.info(
            "Create QoS %s when updating %s", self.qos_name1, self.net1
        )
        if not ll_networks.update_network_in_datacenter(
            positive=True, network=self.net1, datacenter=conf.DC_NAME,
            qos_dict={
                "datacenter": conf.DC_NAME,
                "qos_name": self.qos_name1,
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s when creating QoS %s on %s" %
                (self.net1, self.qos_name1, conf.DC_NAME)
            )

    @polarion("RHEVM3-14272")
    def test_02_create_qos_when_update_network_with_qos(self):
        """
        Create another QoS when editing the same network
        """
        logger.info(
            "Create QoS %s when updating %s", self.qos_name2, self.net1
        )
        if not ll_networks.update_network_in_datacenter(
            positive=True, network=self.net1, datacenter=conf.DC_NAME,
            qos_dict={
                "datacenter": conf.DC_NAME,
                "qos_name": self.qos_name2,
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s when creating QoS %s on %s" %
                (self.net1, self.qos_name2, conf.DC_NAME)
            )

    @bzd({"1278297": {'engine': None, 'version': ["3.6"]}})
    @polarion("RHEVM3-14273")
    def test_03_unlimited_qos_when_update_network(self):
        """
        Update the network with unlimited QoS
        """
        logger.info("Update network not to have QoS (unlimited)")
        if not ll_networks.update_network_in_datacenter(
            positive=True, network=self.net1, datacenter=conf.DC_NAME,
            qos_dict={}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't update %s to have unlimited QoS" % self.net1
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the host
        Remove Host Network QoS
        """
        for qos in (cls.qos_name1, cls.qos_name2):
            net_helper.remove_qos_from_dc(qos_name=qos)


@attr(tier=2)
class TestHostNetQOSCase10(TestHostNetworkQoSTestCaseBase):
    """
    Attach network with QoS to host NIC
    """
    __test__ = True
    net = conf.NETS[10][0]
    qos_dict = {
        "rt": (conf.TEST_VALUE - 1) * MB_CONVERTER,
        "ul": (conf.TEST_VALUE + 1) * MB_CONVERTER,
        "ls": conf.TEST_VALUE
    }

    @classmethod
    def setup_class(cls):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net,
                    "nic": conf.HOST_1_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_realtime": conf.TEST_VALUE - 1,
                        "outbound_average_upperlimit": conf.TEST_VALUE + 1
                    }
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
                "Failed to attach %s to %s on %s" % (
                    cls.net, conf.HOST_1_NICS[1], conf.HOST_1
                )
            )

    @polarion("RHEVM3-6534")
    def test_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        helper.cmp_qos_with_vdscaps(
            net=conf.NETS[10][0], qos_dict=self.qos_dict
        )
