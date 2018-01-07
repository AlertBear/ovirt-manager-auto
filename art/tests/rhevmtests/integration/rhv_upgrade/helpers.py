"""
Upgrade helper functions
"""

import logging

import pytest
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.low_level import events as ll_events
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.unittest_lib import testflow

import config

logger = logging.getLogger(__name__)


def check_host_upgrade_wait_for_status(host_name):
    """
    Check for update of packages on host by engine and wait for event that
    it is finnished

    Args:
        host_name (str): Name of the host to be check upgrade for

    Returns:
        bool: True if action finished without timeout, otherwise False

    Raises:
        APITimeouet: When check for upgrade did not start
    """
    testflow.step("Acquiring last event ID")
    last_event_id = ll_events.get_max_event_id()

    testflow.step("Triggering check of updates")
    if not ll_hosts.check_host_upgrade(host_name):
        return False

    testflow.step(
        "Waiting for message in events - %s",
        config.HOST_AVAILABLE_UPDATES_STARTED
    )
    if not ll_events.wait_for_event(
        config.HOST_AVAILABLE_UPDATES_STARTED, start_id=last_event_id
    ):
        raise APITimeout("Host upgraded started not found in events")

    testflow.step(
        "Waiting for message in events - %s",
        config.HOST_AVAILABLE_UPDATES_FINISHED
    )
    if not ll_events.wait_for_event(
        config.HOST_AVAILABLE_UPDATES_FINISHED, start_id=last_event_id
    ):
        testflow.step(
            "Check for update finished timed out, waiting for event - %s",
            config.HOST_AVAILABLE_UPDATES_FAILED
        )

        if not ll_events.wait_for_event(
            config.HOST_AVAILABLE_UPDATES_FAILED, start_id=last_event_id
        ):
            raise APITimeout("Host upgraded failed not found in events")
        return False
    return True


def upgrade_hosts(host_list):
    """
    This function upgrades RHVH hosts to new version 1 by 1,
    in case of running VM on host it is migrated on moving
    host to maintenance

    Args:
        host_list (list): list of hostnames

    Return:
        bool: True on success
    """
    testflow.step("Machines for upgrade - %s", " ,".join(host_list))
    if not host_list:
        pytest.skip("No hosts of this type available")

    for host_machine in host_list:
        testflow.step(
            "Trigger check by engine for available updates on host - %s",
            host_machine
        )
        if not check_host_upgrade_wait_for_status(host_machine):
            return False

        testflow.step("Check upgrade available on %s", host_machine)
        if ll_hosts.is_upgrade_available(host_machine):
            testflow.step("Upgrading host %s", host_machine)
            try:
                assert ll_hosts.upgrade_host(host_machine)
            except APITimeout as e:
                logger.error("Host upgrade failed on API timeout - %s", e)
                return False
        else:
            logger.warn("Upgrade not available for host %s", host_machine)
    return True
