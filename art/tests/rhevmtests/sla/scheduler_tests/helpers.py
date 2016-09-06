"""
Helper for scheduler tests
"""
import logging

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.helpers as rhevm_helpers
import rhevmtests.sla.config as conf
import rhevmtests.sla.helpers as sla_helpers

logger = logging.getLogger(__name__)


def is_balancing_happen(
    host_name,
    expected_num_of_vms,
    negative=False,
    sampler_timeout=conf.SHORT_BALANCE_TIMEOUT,
    sampler_sleep=conf.SAMPLER_SLEEP
):
    """
    Check if balance module works correct

    Args:
        host_name (str): Host name
        expected_num_of_vms (int): Expected number of VM's on host
        negative (bool): Wait for positive or negative status
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep

    Returns:
        bool: True, if host has expected number of vms, otherwise False
    """
    log_msg = (
        conf.BALANCE_LOG_MSG_NEGATIVE
        if negative else conf.BALANCE_LOG_MSG_POSITIVE
    )
    logger.info(log_msg, host_name)
    return sla_helpers.wait_for_active_vms_on_host(
        host_name=host_name,
        expected_num_of_vms=expected_num_of_vms,
        sampler_timeout=sampler_timeout,
        sampler_sleep=sampler_sleep,
        negative=negative
    )


def migrate_vm_by_maintenance_and_get_destination_host(src_host, vm_name):
    """
    Put VM host to maintenance and get VM destination host

    Args:
        src_host (str): Source host name
        vm_name (str): VM name

    Returns:
        str: Destination host name
    """
    if not ll_hosts.deactivateHost(positive=True, host=src_host):
        return ""
    return ll_vms.get_vm_host(vm_name=vm_name)


def stop_cpu_load_on_all_hosts():
    """
    1) Stop CPU load on all GE hosts
    """
    logger.info("Free all host CPU's from loading")
    sla_helpers.stop_load_on_resources(
        hosts_and_resources_l=[
            {conf.RESOURCE: conf.VDS_HOSTS[:3], conf.HOST: conf.HOSTS[:3]}
        ]
    )


def change_engine_config_low_utilization_value(value):
    """
    1) Change engine-config LowUtilizationForEvenlyDistribute value
    2) Wait until engine storage domain will be active

    Args:
        value (int): New value

    Returns:
        bool: True, if update succeed, otherwise False
    """
    logger.info(
        "Change engine-config parameter %s to %s",
        conf.ENGINE_CONFIG_LOW_UTILIZATION, value
    )
    cmd = [
        "{0}={1}".format(conf.ENGINE_CONFIG_LOW_UTILIZATION, value)
    ]
    if not conf.ENGINE.engine_config(action='set', param=cmd).get('results'):
        logger.error(
            "Failed to set %s option to %s",
            conf.ENGINE_CONFIG_LOW_UTILIZATION, value
        )
        return False
    if not rhevm_helpers.wait_for_engine_api():
        return False
    return True
