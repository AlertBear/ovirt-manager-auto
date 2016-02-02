#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Functions for nic_slave_bond_fault_event_log job
"""

import logging
import config as conf
from art.core_api import apis_utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.events as ll_events

logger = logging.getLogger("Int_Fault_Event_Helper")


class EventException(Exception):
    """
    Raised when event not found
    """

    def __init__(self, code, state, interface):
        self.code = code
        self.state = state
        self.interface = interface

    def __str__(self):
        msg = (
            "Event not found: event code={0}, state={1}, interface={2}"
            .format(self.code, self.state, self.interface)
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


def set_nic_down(nic):
    """
    Set NIC down on host

    :param nic: NIC to set down
    :type nic: str
    :return: True if NIC is down otherwise False
    :rtype: bool
    """
    return conf.VDS_HOSTS_0.network.if_down(nic=nic)


def set_nic_up(nic):
    """
    Set NIC up on host

    :param nic: NIC to set up
    :type nic: str
    :return: True if NIC is up otherwise False
    :rtype: bool
    """
    return conf.VDS_HOSTS_0.network.if_up(nic=nic)


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
    # make sure bond is up in engine
    def is_bond_up():
        try:
            return "up" == ll_hosts.get_host_nic(
                conf.HOSTS[0], conf.BOND_0
            ).status.state
        except AttributeError:
            return False

    logger.info("Wait till %s is up", conf.BOND_0)
    sampler = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT * 2, sleep=1,
        func=is_bond_up
    )
    if not sampler.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION

    # set slave 1 down and check for event log
    set_link_status(
        nic_state=conf.STATE_DOWN, nic=conf.HOST_NICS[2],
        code=conf.HOST_BOND_SLAVE_STATE_DOWN, slave_id=1
    )
    # set slave 2 down and check for event log
    set_link_status(
        nic_state=conf.STATE_DOWN, nic=conf.HOST_NICS[3],
        code=conf.HOST_BOND_SLAVE_STATE_DOWN, slave_id=2
    )

    # set slave 1 up and check for event log
    set_link_status(
        nic_state=conf.STATE_UP, nic=conf.HOST_NICS[2],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=1
    )

    # set slave 2 up and check for event log
    set_link_status(
        nic_state=conf.STATE_UP, nic=conf.HOST_NICS[3],
        code=conf.HOST_BOND_SLAVE_STATE_UP, slave_id=2
    )

    # ip link set down the BOND interface and check for event log.
    set_link_status(
        nic_state=conf.STATE_DOWN, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_DOWN
    )

    # ip link set up the BOND interface and check for event log.
    set_link_status(
        nic_state=conf.STATE_UP, nic=conf.BOND_0,
        code=conf.HOST_INTERFACE_STATE_UP
    )


def nic_fault():
    """
    ip link set down eth1 and check for event log.
    ip link set up eth1 and check for event log.
    """
    # ip link set down eth1 and check for event log
    set_link_status(
        nic_state=conf.STATE_DOWN, nic=conf.HOST_NICS[1],
        code=conf.HOST_INTERFACE_STATE_DOWN
    )
    # ip link set up eth1 and check for event log
    set_link_status(
        nic_state=conf.STATE_UP, nic=conf.HOST_NICS[1],
        code=conf.HOST_INTERFACE_STATE_UP
    )


def set_link_status(nic, code, nic_state=None, slave_id=None):
    """
    ip link set up/down host NIC and check for event log.

    :param nic: NIC name
    :type nic: str
    :param code: Event type code
    :type code: int
    :param nic_state: Desired NIC state
    :type nic_state: str
    :param slave_id: BOND slave ID
    :type slave_id: int
    :raise: EventException
    """
    bond_log = "(bond slave %s)" % slave_id if slave_id else ""
    last_event = ll_events.get_last_event(code=code)
    if nic_state:
        logger.info("Set %s %s %s", nic, nic_state, bond_log)
        int_func = eval("set_nic_%s" % nic_state)
        if not int_func(nic=nic):
            raise SetNicException(state=nic_state, interface=nic)

    event_log_logging(code=code, state=nic_state, interface=nic)
    if not ll_events.find_event_sampler(
        last_event=last_event, event_code=code, content=nic,
        timeout=conf.SAMPLER_TIMEOUT, sleep=1
    ):
        raise EventException(
            code=code, state=nic_state, interface=nic
        )
