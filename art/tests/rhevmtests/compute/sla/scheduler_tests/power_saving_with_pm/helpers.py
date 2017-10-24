"""
Helpers for Power Saving with power management test
"""
import logging

import art.unittest_lib as u_lib
import rhevmtests.compute.sla.config as sla_conf
import rhevmtests.helpers as rhevm_helpers
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler

logger = logging.getLogger(__name__)


def get_host_pm_state(pm_command_executor, host_pm_details, expected_state):
    """
    Verify that the host power management state equals to expected one

    Args:
        pm_command_executor (VDS): Host resource to execute the command
        host_pm_details (dict): Target host power management details
        expected_state (str): Expected power management state of the host
            on, off, unknown

    Returns:
        bool: True, if the host power management state equals
            to expected_state, otherwise False
    """
    pm_command_args = {
        "addr": host_pm_details.get(sla_conf.PM_ADDRESS),
        "port": host_pm_details.get(sla_conf.PM_SLOT, "0"),
        "agent": host_pm_details.get(sla_conf.PM_TYPE),
        "username": host_pm_details.get(sla_conf.PM_USERNAME),
        "password": host_pm_details.get(sla_conf.PM_PASSWORD),
        "action": "status"
    }
    if sla_conf.PM_OPTIONS in host_pm_details:
        pm_command_args["options"] = host_pm_details[sla_conf.PM_OPTIONS]

    out = pm_command_executor.vds_client(cmd="fenceNode", args=pm_command_args)
    if not out:
        logger.error(
            "%s: failed to run power management command",
            pm_command_executor
        )
        return False
    pm_state = out.get("power")
    logger.debug(
        "%s: power management state %s", pm_command_executor, pm_state
    )
    return pm_state == expected_state


def wait_for_host_pm_state(
    pm_command_executor,
    host_resource,
    expected_state,
    sampler_timeout=sla_conf.SAMPLER_TIMEOUT,
    sampler_sleep=30
):
    """
    Wait until the host power management state will be equal to expected one

    Args:
        pm_command_executor (VDS): Host resource to execute the command
        host_resource (VDS): Target host resource
        expected_state (str): Expected power management state of the host
            on, off, unknown
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep

    Returns:
        bool: True, if the host power management state equals to
            the expected_state, otherwise False
    """
    host_fqdn = host_resource.fqdn
    host_pm = (
        sla_conf.PMS.get(host_fqdn) or
        rhevm_helpers.get_pm_details(host_fqdn).get(host_fqdn)
    )
    if not host_pm:
        logger.error("%s: does not have PM", host_resource)
        return False

    if host_pm.get(sla_conf.PM_TYPE) == sla_conf.PM_TYPE_DRAC7:
        host_pm[sla_conf.PM_TYPE] = sla_conf.PM_TYPE_IPMILAN
        host_pm[sla_conf.PM_OPTIONS] = "privlvl=operator\ndelay=10\nlanplus=1"

    sampler = TimeoutingSampler(
        timeout=sampler_timeout,
        sleep=sampler_sleep,
        func=get_host_pm_state,
        pm_command_executor=pm_command_executor,
        host_pm_details=host_pm,
        expected_state=expected_state
    )
    u_lib.testflow.step(
        "Wait for host %s power management state %s", host_fqdn, expected_state
    )
    try:
        for sample in sampler:
            if sample:
                return True
    except APITimeout:
        logger.error(
            "Host %s power management state does not equal to %s",
            host_fqdn, expected_state
        )
        return False
