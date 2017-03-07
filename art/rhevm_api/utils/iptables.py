import art.rhevm_api.utils.storage_api as st_api
from art.rhevm_api.tests_lib.low_level import hosts
from art.test_handler.settings import opts
import logging

logger = logging.getLogger("art.utils.iptables")
ENUMS = opts['elements_conf']['RHEVM Enums']

BLOCK_FUNCTION = st_api.blockOutgoingConnection
UNBLOCK_FUNCTION = st_api.unblockOutgoingConnection
BLOCK = 'block'
UNBLOCK = 'unblock'

HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["host_state_non_responsive"]
HOST_UP = ENUMS['search_host_state_up']


def _perform_iptables_action_and_wait(action, source,
                                      s_user, s_pass,
                                      destination, wait_for_entity,
                                      expected_state):
    """
    Description: block/unblock connection from source to destination,
    and wait_for_entity state to change to expected_state
    Author: ratamir
    Parameters:
        * action - the action that need to preform
                   (i.e. BLOCK or UNBLOCK)
        * source - block/unblock connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - block/unblock connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise

    """
    logger.info("%sing connection from %s to %s", action, source,
                destination)

    function = BLOCK_FUNCTION if action == BLOCK else UNBLOCK_FUNCTION
    success = function(source, s_user, s_pass, destination)
    if not success:
        logger.warning("%sing connection to %s failed. result was %s."
                       % (action, destination, success))
        return success

    logger.info("wait for state : '%s' ", expected_state)
    response = hosts.wait_for_hosts_states(True, wait_for_entity,
                                           states=expected_state)

    host_state = hosts.get_host_status(wait_for_entity)
    if not response:
        logger.warning("Host should be in status %s but it's in status %s"
                       % (expected_state, host_state))
    return response


def block_and_wait(source, s_user, s_pass, destination,
                   wait_for_entity,
                   expected_state=HOST_NONOPERATIONAL):
    """
    block connection from source to destination, and wait_for_entity
    state to change to expected_state
    Author: ratamir
    Parameters:
        * source - block connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - block connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise
    """
    return _perform_iptables_action_and_wait(
        BLOCK, source, s_user, s_pass,
        destination, wait_for_entity, expected_state)


def unblock_and_wait(source, s_user, s_pass, destination,
                     wait_for_entity,
                     expected_state=HOST_UP):
    """
    unblock connection from source to destination, and wait_for_entity
    state to change to expected_state
    Author: ratamir
    Parameters:
        * source - unblock connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - unblock connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise
    """

    return _perform_iptables_action_and_wait(
        UNBLOCK, source, s_user, s_pass,
        destination, wait_for_entity, expected_state)
