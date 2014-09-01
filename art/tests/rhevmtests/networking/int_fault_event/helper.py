"""
Functions for nic_slave_bond_fault_event_log job
"""
from art.rhevm_api.tests_lib.low_level.hosts import ifdownNic, ifupNic
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_utils import TimeoutingSampler
from rhevmtests.networking import config
import logging

logger = logging.getLogger(__name__)
EVENT_API = get_api("event", "events")


def if_down_nic(nic):
    """
    Set NIC down on host
    :param nic: NIC to set down
    :return: True is NIC down otherwise False
    """
    return ifdownNic(host=config.HOSTS[0],
                     root_password=config.HOSTS_PW,
                     nic=nic)


def if_up_nic(nic):
    """
    Set NIC up on host
    :param nic: NIC to set up
    :return: True is NIC down otherwise False
    """
    return ifupNic(host=config.HOSTS[0],
                   root_password=config.HOSTS_PW,
                   nic=nic)


def find_event(last_event_id, event_code, interface, state):
    """
    Find event in RHEV-M event log by event code and keywords in event
    description. Search for the event only from last event ID.
    :param last_event_id: Event ID to search from
    :param event_code: Event code to search for
    :param interface: Interface to search in description
    :param state: NIC state to search in description
    :return: True if event was found otherwise False
    """
    for event in EVENT_API.get(absLink=False):
        if event.get_id() == last_event_id:
            return False
        event_description = event.get_description()
        logger.info("Current event: %s", event_description)
        if (event.get_code() == event_code and state in event_description
                and interface in event_description):
            logger.info("Event found: %s", event_description)
            return True

    return False


def find_event_sampler(last_event_id, event_code, interface, state):
    """
    Run find_event function in sampler.
    :param last_event_id: Event ID to search from
    :param event_code: Event code to search for
    :param interface: Interface to search in description
    :param state: NIC state to search in description
    :return: True if event was found otherwise False
    """
    sample = TimeoutingSampler(
        timeout=config.SAMPLER_TIMEOUT,
        sleep=1,
        func=find_event,
        last_event_id=last_event_id,
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
    info = "Checking for event log: event code={0}, state={1}, " \
           "interface={2}".format(code, state, interface)
    logger.info(info)
