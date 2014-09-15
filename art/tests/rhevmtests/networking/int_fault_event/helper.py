"""
Functions for nic_slave_bond_fault_event_log job
"""

from art.rhevm_api.tests_lib.low_level.hosts import ifdownNic, ifupNic
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_utils import TimeoutingSampler
from rhevmtests.networking import config
import logging

logger = logging.getLogger("int_fault_event_helper")

EVENT_API = get_api("event", "events")
HOST_INTERFACE_STATE_UP = 609
HOST_INTERFACE_STATE_DOWN = 610
HOST_BOND_SLAVE_STATE_UP = 611
HOST_BOND_SLAVE_STATE_DOWN = 612
STATE_UP = "up"
STATE_DOWN = "down"
SAMPLER_TIMEOUT = 60


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


def if_down_nic(nic, wait=True):
    """
    Set NIC down on host
    :param nic: NIC to set down
    :return: True if NIC is down otherwise False
    """
    return ifdownNic(
        host=config.HOSTS_IP[0], root_password=config.HOSTS_PW, nic=nic,
        wait=wait
    )


def if_up_nic(nic, wait=True):
    """
    Set NIC up on host
    :param nic: NIC to set up
    :return: True if NIC is down otherwise False
    """
    return ifupNic(
        host=config.HOSTS_IP[0], root_password=config.HOSTS_PW, nic=nic,
        wait=wait
    )


def find_event(last_event, event_code, interface, state):
    """
    Find event in RHEV-M event log by event code and keywords in event
    description. Search for the event only from last event ID.
    :param last_event: Event object to search from
    :param event_code: Event code to search for
    :param interface: Interface to search in description
    :param state: NIC state to search in description
    :return: True if event was found otherwise False
    """
    processed_events = []
    all_events = EVENT_API.get(absLink=False)
    last_event_index = [event.id for event in all_events].index(last_event.id)
    logger.info("Last event ID: %s", last_event.id)
    for event in all_events[:last_event_index]:
            event_id = event.get_id()
            event_description = event.get_description()
            if (
                event.get_code() == event_code and state in event_description
                and interface in event_description
            ):
                logger.info("Event found: %s", event_description)
                return True
            processed_events.append((event_id, event_description))

    events = processed_events if processed_events else "No new events"
    logger.info("processed events: %s", events)
    return False


def find_event_sampler(last_event, event_code, interface, state):
    """
    Run find_event function in sampler.
    :param last_event: Event object to search from
    :param event_code: Event code to search for
    :param interface: Interface to search in description
    :param state: NIC state to search in description
    :return: True if event was found otherwise False
    """
    sample = TimeoutingSampler(
        timeout=SAMPLER_TIMEOUT,
        sleep=5,
        func=find_event,
        last_event=last_event,
        event_code=event_code,
        interface=interface,
        state=state
    )
    return sample.waitForFuncStatus(result=True)


def event_log_logging(code, state, interface):
    """
    Generate log for event log search function
    :param code: Event code
    :param state: NIC state to search in description
    :param interface: Interface to search in description
    :return: logger info or error
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
    last_event = EVENT_API.get(absLink=False)[0]

    # set slave 1 and 2 down and check for event log
    set_link_down(last_event, config.VDS_HOSTS[0].nics[2], 1)
    set_link_down(last_event, config.VDS_HOSTS[0].nics[3], 2)

    # Check event log for bond down (all slaves are down)
    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.BOND[0], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0], True
        )

    # set slave 1 up and check for event log
    set_link_up(last_event, config.VDS_HOSTS[0].nics[2], 1)

    # Check event log for bond up (slave1 is up)
    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_UP,
        interface=config.BOND[0], state=STATE_UP
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0], True
        )

    # # set slave 2 up and check for event log
    set_link_up(last_event, config.VDS_HOSTS[0].nics[3], 2)

    # ip link set down the BOND interface and check for event log.
    last_event = EVENT_API.get(absLink=False)[0]
    logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
    if_down_nic(nic=config.BOND[0], wait=False)

    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.BOND[0], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0], True
        )

    # ip link set up the BOND interface and check for event log.
    logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
    if_up_nic(nic=config.BOND[0], wait=False)
    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.BOND[0], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0], True
        )


def nic_fault():
    """
    ip link set down eth1 and check for event log.
    ip link set up eth1 and check for event log.
    """
    last_event = EVENT_API.get(absLink=False)[0]

    # ip link set down eth1 and check for event log
    logger.info("Set %s %s", config.VDS_HOSTS[0].nics[1], STATE_DOWN)
    if not if_down_nic(nic=config.VDS_HOSTS[0].nics[1]):
        raise SetNicException(STATE_DOWN, config.VDS_HOSTS[0].nics[1])

    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.VDS_HOSTS[0].nics[1]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.VDS_HOSTS[0].nics[1], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.VDS_HOSTS[0].nics[1],
            True
        )

    # ip link set up eth1 and check for event log
    logger.info("Set %s %s", config.VDS_HOSTS[0].nics[1], STATE_UP)
    if not if_up_nic(nic=config.VDS_HOSTS[0].nics[1]):
        raise SetNicException(STATE_UP, config.VDS_HOSTS[0].nics[1])

    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.VDS_HOSTS[0].nics[1]
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_UP,
        interface=config.VDS_HOSTS[0].nics[1], state=STATE_UP
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.VDS_HOSTS[0].nics[1],
            True
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
    last_event = EVENT_API.get(absLink=False)[0]

    # set down slaves 1 and 2 and check for event log
    empty_bond_link_down(last_event, config.VDS_HOSTS[0].nics[2], 1)
    empty_bond_link_down(last_event, config.VDS_HOSTS[0].nics[3], 2)

    # Check event log for bond down (all slaves are down)
    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.BOND[0], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0], False
        )

    # ip link set up slave1 of the BOND and check for event log.
    empty_bond_link_up(last_event, config.VDS_HOSTS[0].nics[2], 1)

    # Check event log for bond up (slave1 is up)
    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_BOND_SLAVE_STATE_UP,
        interface=config.BOND[0], state=STATE_UP
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0], False
        )

    # ip link set up slave2 of the BOND and check for event log.
    empty_bond_link_up(last_event, config.VDS_HOSTS[0].nics[3], 2)

    # ip link set down the BOND interface and check for event log.
    logger.info("Set %s %s", config.BOND[0], STATE_DOWN)
    last_event = EVENT_API.get(absLink=False)[0]
    if_down_nic(nic=config.BOND[0], wait=False)

    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.BOND[0], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.BOND[0], False
        )

    # ip link set up the BOND interface and check for event log.
    logger.info("Set %s %s", config.BOND[0], STATE_UP)
    if_up_nic(nic=config.BOND[0], wait=False)

    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_UP,
        interface=config.BOND[0], state=STATE_UP
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.BOND[0], False
        )


def empty_nic_fault():
    """
    ip link set down eth1 and check for event log.
    ip link set up eth1 and check for event log.
    """
    last_event = EVENT_API.get(absLink=False)[0]

    # ip link set down eth1 and check for event log
    logger.info("Set %s %s", config.VDS_HOSTS[0].nics[1], STATE_DOWN)
    if not if_down_nic(nic=config.VDS_HOSTS[0].nics[1]):
        raise SetNicException(STATE_DOWN, config.VDS_HOSTS[0].nics[1])

    event_log_logging(
        HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.VDS_HOSTS[0].nics[1]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_DOWN,
        interface=config.VDS_HOSTS[0].nics[1], state=STATE_DOWN
    ):
        raise EventException(
            HOST_INTERFACE_STATE_DOWN, STATE_DOWN, config.VDS_HOSTS[0].nics[1],
            False
        )

    # ip link set up eth1 and check for event log
    logger.info("Set %s %s", config.VDS_HOSTS[0].nics[1], STATE_UP)
    if not if_up_nic(nic=config.VDS_HOSTS[0].nics[1]):
        raise SetNicException(STATE_UP, config.VDS_HOSTS[0].nics[1])

    event_log_logging(
        HOST_INTERFACE_STATE_UP, STATE_UP, config.VDS_HOSTS[0].nics[1]
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_INTERFACE_STATE_UP,
        interface=config.VDS_HOSTS[0].nics[1], state=STATE_UP
    ):
        raise EventException(
            HOST_INTERFACE_STATE_UP, STATE_UP, config.VDS_HOSTS[0].nics[1],
            False
        )


def set_link_down(last_event, nic, slave_id):
    """
    ip link set down slave of the BOND and check for event log.
    :param last_event: last event to search from
    :param nic: NIC name
    :param slave_id: BOND slave ID
    :return: raise EventException if False
    """
    logger.info("Set %s %s (bond slave %s)", nic, STATE_DOWN, slave_id)
    if not if_down_nic(nic=nic):
        raise SetNicException(STATE_DOWN, nic)

    event_log_logging(
        HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN, nic
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_BOND_SLAVE_STATE_DOWN,
        interface=nic, state=STATE_DOWN
    ):
        raise EventException(
            HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN, nic, True
        )


def set_link_up(last_event, nic, slave_id):
    """
    ip link set up slave of the BOND and check for event log.
    :param last_event: last event to search from
    :param nic: NIC name
    :param slave_id: BOND slave ID
    :return: raise EventException if False
    """
    logger.info("Set %s %s (bond slave %s)", nic, STATE_UP, slave_id)
    if not if_up_nic(nic=nic):
        raise SetNicException(STATE_UP, nic)

    event_log_logging(
        HOST_BOND_SLAVE_STATE_UP, STATE_UP, nic
    )
    if not find_event_sampler(
        last_event=last_event, event_code=HOST_BOND_SLAVE_STATE_UP,
        interface=nic, state=STATE_UP
    ):
        raise EventException(
            HOST_BOND_SLAVE_STATE_UP, STATE_UP, nic, True
        )


def empty_bond_link_down(last_event, nic, slave_id):
    """
    ip link set down slave of the BOND and check for event log.
    :param last_event: last event to search from
    :param nic: NIC name
    :param slave_id: BOND slave ID
    :return: raise EventException if False
    """
    logger.info("Set %s %s (bond slave %s)", nic, STATE_DOWN, slave_id)
    if not if_down_nic(nic=nic):
        raise SetNicException(STATE_DOWN, nic)

    event_log_logging(
        HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN, nic
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_BOND_SLAVE_STATE_DOWN,
        interface=nic, state=STATE_DOWN
    ):
        raise EventException(
            HOST_BOND_SLAVE_STATE_DOWN, STATE_DOWN, nic, False
        )


def empty_bond_link_up(last_event, nic, slave_id):
    """
    ip link set up slave of the BOND and check for event log.
    :param last_event: last event to search from
    :param nic: NIC name
    :param slave_id: BOND slave ID
    :return: raise EventException if False
    """
    logger.info("Set %s %s (bond slave %s)", nic, STATE_DOWN, slave_id)
    if not if_down_nic(nic=nic):
        raise SetNicException(STATE_UP, nic)

    event_log_logging(
        HOST_BOND_SLAVE_STATE_UP, STATE_UP, nic
    )
    if find_event_sampler(
        last_event=last_event, event_code=HOST_BOND_SLAVE_STATE_UP,
        interface=nic, state=STATE_UP
    ):
        raise EventException(
            HOST_BOND_SLAVE_STATE_UP, STATE_UP, nic, False
        )
