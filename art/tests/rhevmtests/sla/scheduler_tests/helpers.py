"""
Helper for scheduler tests
"""
import logging

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
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
    u_libs.testflow.step(log_msg, host_name)

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
    if not ll_hosts.deactivate_host(positive=True, host=src_host):
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


def configure_pm_on_hosts(hosts):
    """
    Configure power management on hosts

    Args:
        hosts (dict): {host_name: host_resource,...}

    Returns:
        bool: True, if power management configuration succeeds, otherwise False
    """
    for host_name, host_resource in hosts.iteritems():
        host_fqdn = host_resource.fqdn
        host_pm = (
            conf.PMS.get(host_fqdn) or
            rhevm_helpers.get_pm_details(host_fqdn).get(host_fqdn)
        )
        if not host_pm:
            logger.error("Host %s does not have PM" % host_name)
            return False
        options = {
            "slot": host_pm.get(conf.PM_SLOT),
            "port": host_pm.get(conf.PM_PORT)
        }
        agent_options = {}
        for option_name, option_value in options.iteritems():
            if option_value:
                agent_options[option_name] = option_value
        agent = {
            "agent_type": host_pm.get(conf.PM_TYPE),
            "agent_address": host_pm.get(conf.PM_ADDRESS),
            "agent_username": host_pm.get(conf.PM_USERNAME),
            "agent_password": host_pm.get(conf.PM_PASSWORD),
            "concurrent": False,
            "order": 1,
            "options": agent_options
        }
        u_libs.testflow.setup(
            "Add power management agent %s to the host %s", agent, host_name
        )
        if not hl_hosts.add_power_management(
            host_name=host_name,
            pm_automatic=True,
            pm_agents=[agent]
        ):
            return False
    return True


def add_affinity_scheduler_policy():
    """
    Add scheduling policy for affinity tests
    """
    u_libs.testflow.setup(
        "Add scheduling policy %s", conf.AFFINITY_POLICY_NAME
    )
    assert ll_sch_policies.add_new_scheduling_policy(
        name=conf.AFFINITY_POLICY_NAME
    )
    for units_names, unit_type in zip(
        (conf.AFFINITY_SCHEDULER_FILTERS, conf.AFFINITY_SCHEDULER_WEIGHTS),
        (ll_sch_policies.FILTER_TYPE, ll_sch_policies.WEIGHT_TYPE)
    ):
        factor = 10 if unit_type == ll_sch_policies.WEIGHT_TYPE else None
        u_libs.testflow.setup("Add %s's to the scheduling policy", unit_type)
        for unit_name in units_names:
            assert ll_sch_policies.add_scheduling_policy_unit(
                policy_name=conf.AFFINITY_POLICY_NAME,
                unit_name=unit_name,
                unit_type=unit_type,
                factor=factor
            )
