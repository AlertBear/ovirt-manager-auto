"""
Testing Display of NIC Slave/Bond fault on RHEV-M Event Log
1 DC, 1 Cluster, 1 Host will be created for testing.
"""

import helper
import logging
from nose.tools import istest
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from art.rhevm_api.tests_lib.low_level.networks import remove_label, add_label
from art.rhevm_api.utils.test_utils import get_api
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
from rhevmtests.networking import config
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, remove_all_networks
)

logger = logging.getLogger(__name__)
EVENT_API = get_api("event", "events")
HOST_INTERFACE_STATE_UP = 609
HOST_INTERFACE_STATE_DOWN = 610
HOST_BOND_SLAVE_STATE_UP = 611
HOST_BOND_SLAVE_STATE_DOWN = 612
STATE_UP = "up"
STATE_DOWN = "down"


class NicFaultTestCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not remove_label(host_nic_dict={config.HOSTS[0]: config.HOST_NICS}):
            raise NetworkException("Couldn't remove labels from Hosts")

        if not (remove_all_networks(datacenter=config.DC_NAME[0],
                                    mgmt_network=config.MGMT_BRIDGE,
                                    cluster=config.CLUSTER_NAME[0]) and
                createAndAttachNetworkSN(host=config.HOSTS[0],
                                         network_dict={},
                                         auto_nics=[config.HOST_NICS[0]])):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class NicFault1(NicFaultTestCaseBase):
    """
    1. Attach label to host interface
    2. ip link set down the host interface
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach label to host interface
        """
        logger.info("Attach label %s to %s on %s", config.LABEL_LIST[0],
                    config.HOST_NICS[1], config.HOSTS[0])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]:
                                        [config.HOST_NICS[1]]}):
            raise NetworkException("Couldn't add label %s to the Host "
                                   "NIC %s but should" %
                                   (config.LABEL_LIST[0], config.HOST_NICS[1]))

    @istest
    @tcms(13885, 366409)
    def label_nic_fault(self):
        """
        Set eth1 down and check for event log.
        Set eth1 up and check for event log
        """
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()

        logger.info("Set %s %s", config.HOST_NICS[1], STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[1])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.HOST_NICS[1],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        logger.info("Set %s %s", config.HOST_NICS[1], STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[1])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_UP,
                                         interface=config.HOST_NICS[1],
                                         state=STATE_UP):
            raise NetworkException("Event not found")


@attr(tier=1)
class NicFault2(NicFaultTestCaseBase):
    """
    1. Attach required network to host NIC
    2. ip link set down the host NIC
    3. ip link set up the host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach required network to host NIC
        """
        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1]}}

        logger.info("Attach %s network to DC/Cluster/Host", config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

    @istest
    @tcms(13885, 366410)
    def required_nic_fault(self):
        """
        ip link set down eth1 and check for event log.
        ip link set up eth1 and check for event log.
        """
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()

        # ip link set down eth1 and check for event log
        logger.info("Set %s %s", config.HOST_NICS[1], STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[1])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.HOST_NICS[1],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set up eth1 and check for event log
        logger.info("Set %s %s", config.HOST_NICS[1], STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[1])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_UP,
                                         interface=config.HOST_NICS[1],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Activating the host if needed")
        if not activate_host_if_not_up(config.HOSTS[0]):
            raise NetworkException("Failed to activate the host")

        logger.info("Call LabelTestCaseBase teardown")
        super(NicFault2, cls).teardown_class()


@attr(tier=1)
class NicFault3(NicFaultTestCaseBase):
    """
    No setup needed
    """
    __test__ = True

    @istest
    @tcms(13885, 366412)
    def empty_nic_fault(self):
        """
        ip link set down eth1 and check for event log.
        ip link set up eth1 and check for event log.
        """
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()

        # ip link set down eth1 and check for event log
        logger.info("Set %s %s", config.HOST_NICS[1], STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[1])
        if helper.find_event_sampler(last_event_id=last_event_id,
                                     event_code=HOST_INTERFACE_STATE_DOWN,
                                     interface=config.HOST_NICS[1],
                                     state=STATE_DOWN):
            raise NetworkException("Event found but shouldn't")

        # ip link set up eth1 and check for event log
        logger.info("Set %s %s", config.HOST_NICS[1], STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[1]))

        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[1])
        if helper.find_event_sampler(last_event_id=last_event_id,
                                     event_code=HOST_INTERFACE_STATE_UP,
                                     interface=config.HOST_NICS[1],
                                     state=STATE_UP):
            raise NetworkException("Event found but shouldn't")


@attr(tier=1)
class NicFault4(NicFaultTestCaseBase):
    """
    1. Attach label to BOND
    2. ifconfig down slave1 of the BOND
    3. ifconfig down slave2 of the BOND
    4. ifconfig up slave1 of the BOND
    5. ifconfig up slave2 of the BOND
    6. ifconfig down the BOND interface
    7. ifconfig up the BOND interface
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach label to BOND
        """
        local_dict1 = {None: {'nic': config.BOND[0],
                              'slaves': [config.HOST_NICS[2],
                                         config.HOST_NICS[3]],
                              'required': 'false'}}

        logger.info("Create Bond %s", config.BOND[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create bond %s " % config.BOND[0])

        logger.info("Attach label %s to %s on %s", config.LABEL_LIST[0],
                    config.BOND[0], config.HOSTS[0])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            raise NetworkException("Couldn't add label %s to the Host "
                                   "NIC %s but should" %
                                   (config.LABEL_LIST[0], config.BOND[0]))

    @istest
    @tcms(13885, 366414)
    def label_bond_fault(self):
        """
        ip link set down slave1 of the BOND and check for event log.
        ip link set down slave2 of the BOND and check for event log.
        ip link set up slave1 of the BOND and check for event log.
        ip link set up slave2 of the BOND and check for event log.
        ip link set down the BOND interface and check for event log.
        ip link set up the BOND interface and check for event log.
        """
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()

        # ip link set down slave1 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 1)", config.HOST_NICS[2],
                    STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[2]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[2]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[2])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_DOWN,
                                         interface=config.HOST_NICS[2],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set down slave2 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 2)", config.HOST_NICS[3],
                    STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[3]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[3]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[3])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_DOWN,
                                         interface=config.HOST_NICS[3],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # Check event log for bond down (all slaves are down)
        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.BOND[0],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set up slave1 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 1)", config.HOST_NICS[2], STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[2]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[2]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[2])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_UP,
                                         interface=config.HOST_NICS[2],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

        # Check event log for bond up (slave1 is up)
        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_UP,
                                         interface=config.BOND[0],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

        # ip link set up slave2 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 2)", config.HOST_NICS[3], STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[3]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[3]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[3])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_UP,
                                         interface=config.HOST_NICS[3],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

        # ip link set down the BOND interface and check for event log.
        logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()
        if not helper.if_down_nic(nic=config.BOND[0]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.BOND[0]))

        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.BOND[0],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set up the BOND interface and check for event log.
        logger.info("Set %s %s", config.BOND[0], STATE_UP)
        if not helper.if_up_nic(nic=config.BOND[0]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.BOND[0]))

        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_UP,
                                         interface=config.BOND[0],
                                         state=STATE_UP):
            raise NetworkException("Event not found")


@attr(tier=1)
class NicFault5(NicFaultTestCaseBase):
    """
    1. Attach required network to BOND
    2. ip link set down slave1 of the BOND
    3. ip link set down slave2 of the BOND
    4. ip link set up slave1 of the BOND
    5. ip link set up slave2 of the BOND
    6. ip link set down the BOND interface
    7. ip link set up the BOND interface
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach required network to BOND
        """
        logger.info("Create and attach network over BOND")
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "true"}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(13885, 366415)
    def required_bond_fault(self):
        """
        ip link set down slave1 of the BOND and check for event log.
        ip link set down slave2 of the BOND and check for event log.
        ip link set up slave1 of the BOND and check for event log.
        ip link set up slave2 of the BOND and check for event log.
        ip link set down the BOND interface and check for event log.
        ip link set up the BOND interface and check for event log.
        """
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()

        # ip link set down slave1 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 1)", config.HOST_NICS[2],
                    STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[2]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[2]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[2])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_DOWN,
                                         interface=config.HOST_NICS[2],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set down slave2 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 2)", config.HOST_NICS[3],
                    STATE_DOWN)
        if not helper.if_down_nic(nic=config.HOST_NICS[3]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.HOST_NICS[3]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN,
                                 config.HOST_NICS[3])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_DOWN,
                                         interface=config.HOST_NICS[3],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # Check event log for bond down (all slaves are down)
        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.BOND[0],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set up slave1 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 1)", config.HOST_NICS[2],
                    STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[2]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[2]))

        helper.event_log_logging(HOST_BOND_SLAVE_STATE_UP, STATE_UP,
                                 config.HOST_NICS[2])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_BOND_SLAVE_STATE_UP,
                                         interface=config.HOST_NICS[2],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

        # Check event log for bond up (slave1 is up)
        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_UP,
                                         interface=config.BOND[0],
                                         state=STATE_UP):
            raise NetworkException("Event not found")

        # ip link set up slave2 of the BOND and check for event log.
        logger.info("Set %s %s (bond slave 2)", config.HOST_NICS[3],
                    STATE_UP)
        if not helper.if_up_nic(nic=config.HOST_NICS[3]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_UP, config.HOST_NICS[3]))

        # ip link set down the BOND interface and check for event log.
        last_event_id = EVENT_API.get(absLink=False)[0].get_id()
        logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
        if not helper.if_down_nic(nic=config.BOND[0]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.BOND[0]))

        helper.event_log_logging(HOST_INTERFACE_STATE_DOWN, STATE_DOWN,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.BOND[0],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

        # ip link set up the BOND interface and check for event log.
        logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
        if not helper.if_up_nic(nic=config.BOND[0]):
            raise NetworkException("Failed to set %s %s" %
                                   (STATE_DOWN, config.BOND[0]))

        helper.event_log_logging(HOST_INTERFACE_STATE_UP, STATE_UP,
                                 config.BOND[0])
        if not helper.find_event_sampler(last_event_id=last_event_id,
                                         event_code=HOST_INTERFACE_STATE_DOWN,
                                         interface=config.BOND[0],
                                         state=STATE_DOWN):
            raise NetworkException("Event not found")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Activating the host if needed")
        if not activate_host_if_not_up(config.HOSTS[0]):
            raise NetworkException("Failed to activate the host")

        logger.info("Call LabelTestCaseBase teardown")
        super(NicFault5, cls).teardown_class()
