#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Functions for nic_slave_bond_fault_event_log job
"""

import time
import logging
import config as conf
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.events as ll_events

logger = logging.getLogger("Int_Fault_Event_Helper")


class EventException(Exception):
    """
    Raised when event not found
    """

    def __init__(self, code, state, interface, positive):
        self.code = code
        self.state = state
        self.interface = interface
        self.positive = positive

    def __str__(self):
        positive = "not found" if self.positive else "found but shouldn't"
        msg = (
            "Event {0}: event code={1}, state={2}, interface={3}"
            .format(positive, self.code, self.state, self.interface)
        )
        return msg


class SetNicException(Exception):
    """
    Raised when NIC is not in expected state
    """

    def __init__(self, state, interface):
        self.state = state
        self.interface = interface

    def __str__(self):
        msg = (
            "Failed to set {0} {1}".format(self.state, self.interface)
        )
        return msg


def set_nic_down(nic, wait=True):
    """
    Set NIC down on host

    :param nic: NIC to set down
    :type nic: str
    :param wait: Wait to NIC status
    :type wait: bool
    :return: True if NIC is down otherwise False
    :rtype: bool
    """
    logger.info("Sleeping for 15 seconds")
    # engine collects events every 15 seconds so need to sleep for
    # 15 to ensure that we catch the next event
    time.sleep(conf.INT_SLEEP)
    return ll_hosts.ifdownNic(
        host=conf.HOST_0_IP, root_password=conf.HOSTS_PW, nic=nic,
        wait=wait
    )


def set_nic_up(nic, wait=True, sleep=True):
    """
    Set NIC up on host

    :param nic: NIC to set up
    :type nic: str
    :param wait: Wait to NIC status
    :type wait: bool
    :param sleep: Time to sleep after nic up command
    :type sleep: int
    :return: True if NIC is up otherwise False
    :rtype: bool
    """
    if sleep:
        logger.info("Sleeping for 15 seconds")
        # engine collects events every 15 seconds so need to sleep for
        # 15 to ensure that we catch the next event
        time.sleep(conf.INT_SLEEP)
    return ll_hosts.ifupNic(
        host=conf.HOST_0_IP, root_password=conf.HOSTS_PW, nic=nic,
        wait=wait
    )


def event_log_logging(code, state, interface):
    """
    Generate log for event log search function

    :param code: Event code
    :type code: int
    :param state: NIC state to search in description
    :type state: str
    :param interface: Interface to search in description
    :type interface: str
    :return: logger info or error
    :rtype: str
    """
    info = (
        "Checking for event log: event code={0}, state={1}, interface={2}"
        .format(code, state, interface)
    )
    logger.info(info)


def bond_fault():
    """
    ip link set down slave1 of the BOND and check for event log.
    ip link set down slave2 of the BOND and check for event log.
    ip link set up slave1 of the BOND and check for event log.
    ip link set up slave2 of the BOND and check for event log.
    ip link set down the BOND interface and check for event log.
    ip link set up the BOND interface and check for event log.
    """
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_DOWN
    )

    # set slave 1 down and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[2], code=conf.HOST_BOND_SLAVE_STATE_DOWN, slave_id=1
    )
    # set slave 2 down and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[3], code=conf.HOST_BOND_SLAVE_STATE_DOWN, slave_id=2
    )
    # Check event log for bond down (all slaves are down)
    set_link_status(
        last_event=bond_last_event, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_DOWN
    )

    # set slave 1 up and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[2],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=1
    )

    # Check event log for bond up (1 slave is up)
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_UP
    )
    set_link_status(
        last_event=bond_last_event, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_UP
    )
    # set slave 2 up and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[3],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=2
    )

    # ip link set down the BOND interface and check for event log.
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_DOWN
    )
    set_link_status(
        last_event=bond_last_event, nic_state=conf.STATE_DOWN, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_DOWN
    )

    # ip link set up the BOND interface and check for event log.
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_UP
    )
    set_link_status(
        last_event=bond_last_event, nic_state=conf.STATE_UP, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_UP
    )


def nic_fault():
    """
    ip link set down eth1 and check for event log.
    ip link set up eth1 and check for event log.
    """
    # ip link set down eth1 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_INTERFACE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[1], code=conf.HOST_INTERFACE_STATE_DOWN
    )

    # ip link set up eth1 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_INTERFACE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[1],
        code=conf.HOST_INTERFACE_STATE_UP
    )


def empty_bond_fault():
    """
    ip link set down slave1 of the BOND and check for event log.
    ip link set down slave2 of the BOND and check for event log.
    ip link set up slave1 of the BOND and check for event log.
    ip link set up slave2 of the BOND and check for event log.
    ip link set down the BOND interface and check for event log.
    ip link set up the BOND interface and check for event log.
    """
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_DOWN
    )
    # set down slaves 1 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[2], code=conf.HOST_BOND_SLAVE_STATE_DOWN,
        slave_id=1, positive=False
    )
    # set down slaves 2 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[3], code=conf.HOST_BOND_SLAVE_STATE_DOWN,
        slave_id=2, positive=False
    )
    # Check event log for bond down (all slaves are down)
    set_link_status(
        last_event=bond_last_event, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_DOWN, positive=False
    )
    # ip link set up slave1 of the BOND and check for event log.
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_UP
    )
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[2],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=1, positive=False
    )
    # Check event log for bond up (1 slave is up)
    set_link_status(
        last_event=bond_last_event, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_UP, positive=False
    )
    # ip link set up slave2 of the BOND and check for event log.
    last_event = ll_events.get_last_event(conf.HOST_BOND_SLAVE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[3],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=2, positive=False
    )
    # ip link set down the BOND interface and check for event log.
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_DOWN
    )
    set_link_status(
        last_event=bond_last_event, nic_state=conf.STATE_DOWN, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_DOWN,
        positive=False
    )
    # ip link set up the BOND interface and check for event log.
    bond_last_event = ll_events.get_last_event(
        conf.HOST_INTERFACE_STATE_UP
    )
    set_link_status(
        last_event=bond_last_event, nic_state=conf.STATE_UP, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_UP, positive=False
    )


def empty_nic_fault():
    """
    ip link set down eth1 and check for event log.
    ip link set up eth1 and check for event log.
    """
    # ip link set down eth1 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_INTERFACE_STATE_DOWN)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_DOWN,
        nic=conf.HOST_NICS[1], code=conf.HOST_INTERFACE_STATE_DOWN,
        positive=False
    )

    # ip link set up eth1 and check for event log
    last_event = ll_events.get_last_event(conf.HOST_INTERFACE_STATE_UP)
    set_link_status(
        last_event=last_event, nic_state=conf.STATE_UP, nic=conf.HOST_NICS[1],
        code=conf.HOST_INTERFACE_STATE_UP,
        positive=False
    )


def set_link_status(
    last_event, nic, code, nic_state=None, slave_id=None, positive=True
):
    """
    ip link set down slave of the BOND and check for event log.

    :param last_event: last event to search from
    :type last_event: int
    :param nic: NIC name
    :type nic: str
    :param code: Event type code
    :type code: int
    :param nic_state: Desired NIC state
    :type nic_state: str
    :param slave_id: BOND slave ID
    :type slave_id: int
    :param positive: Desired return status
    :return: raise EventException
    :rtype: EventException
    """
    bond_log = "(bond slave %s)" % slave_id if slave_id else ""
    if nic_state:
        logger.info("Set %s %s %s", nic, nic_state, bond_log)
        int_func = eval("set_nic_%s" % nic_state)
        if not int_func(nic=nic):
            raise SetNicException(nic_state, nic)

    event_log_logging(code, nic_state, nic)
    res = ll_events.find_event_sampler(
        last_event=last_event, event_code=code, content=nic
    )
    if res != positive:
        raise EventException(code, nic_state, nic, True)
