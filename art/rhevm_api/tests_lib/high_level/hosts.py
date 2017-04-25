#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
High-level functions above data-center
"""

import logging

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.test_handler.exceptions as errors
from art.core_api import apis_exceptions
from art.test_handler.settings import opts
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("art.hl_lib.hosts")
ENUMS = opts['elements_conf']['RHEVM Enums']


def add_hosts(hosts_list, passwords, cluster):
    """
    Description: Adds all hosts from config
    Parameters:
        * hosts_list - list of hosts
        * passwords - list of hosts' passwords
        * cluster - name of the cluster hosts will be placed to
    """
    results = list()
    # Workers should be defined somewhere
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, host in enumerate(hosts_list):
            password = passwords[index]
            logger.info("Adding host %s", host)
            results.append(
                executor.submit(
                    fn=ll_hosts.add_host,
                    name=host,
                    root_password=password,
                    cluster=cluster
                )
            )

    for index, result in enumerate(results):
        if not result.result():
            raise errors.HostException("addHost of host %s failed." %
                                       hosts_list[index])
        logger.debug("Host %s installed", hosts_list[index])

    if not ll_hosts.wait_for_hosts_states(True, ",".join(hosts_list)):
        raise errors.HostException("Some of hosts didn't come to up status")


def move_host_to_another_cluster(host, cluster, activate=True):
    """
    Switch host to different cluster

    :param host: Host name that will be switched to different cluster
    :type host: str
    :param cluster:Cluster name where the host should be moved to
    :type cluster: str
    :param activate: Activate the host after move
    :type activate: bool
    :return: True if succeed to move it False otherwise
    :rtype: bool
    """
    if not ll_hosts.is_host_in_maintenance(positive=True, host=host):
        logger.info("Set %s to maintenance", host)
        if not ll_hosts.deactivate_host(positive=True, host=host):
            logger.error("Failed to set %s to maintenance", host)
            return False

    logger.info("Moving %s to %s", host, cluster)
    if not ll_hosts.update_host(positive=True, host=host, cluster=cluster):
        logger.error("Failed to move %s to %s", host, cluster)
        return False

    if activate:
        logger.info("Activate %s", host)
        if not ll_hosts.activate_host(positive=True, host=host):
            logger.error("Failed to activate %s", host)
            return False
    return True


@ll_general.generate_logs(step=True)
def deactivate_host_if_up(host, host_resource=None):
    """
    Deactivate host if it's not in maintenance

    __author__: 'ratamir'

    Args:
        host (str): Name of the host to deactivate
        host_resource (VDS): Host resource

    Returns:
        bool: True if host was deactivated properly and positive,
            False otherwise.
    """
    if not ll_hosts.is_host_in_maintenance(positive=True, host=host):
        return ll_hosts.deactivate_host(
            positive=True, host=host, host_resource=host_resource
        )
    return True


def deactivate_hosts_if_up(hosts_list):
    """
    Deactivate hosts that are in status up

    __author__ = "ratamir"
    :param hosts_list: List or string of hosts to be deactivated
    :type hosts_list: list
    :returns: True if operation succeded, False otherwise
    :rtype: bool
    """
    if isinstance(hosts_list, str):
        _hosts_list = hosts_list.split(',')
    else:
        _hosts_list = hosts_list[:]

    spm = None
    try:
        spm = ll_hosts.get_spm_host(_hosts_list)
        logger.info("spm host - %s", spm)
    except apis_exceptions.EntityNotFound:
        logger.warning("No SPM host was found from the input hosts_list")

    sorted_hosts = ll_hosts.sort_hosts_by_priority(_hosts_list, False)
    if spm:
        sorted_hosts.remove(spm)
        sorted_hosts.append(spm)

    for host in sorted_hosts:
        if not deactivate_host_if_up(host):
            return False
    return True


def add_power_management(host_name, pm_agents, **kwargs):
    """
    Add fence agents and enable host power management

    Args:
        host_name (str): Host name
        pm_agents (list): Power management agents

    Keyword Args:
        pm_automatic(bool): Enable automatic shutdown of host
            under power saving policy
        pm_proxies (list): Power management proxies

    Returns:
        bool: True, if add succeed, otherwise False

    Examples:
        agent_d = {
            "agent_type": "test_type",
            "agent_address": "test_address",
            "agent_username": "test_username",
            "agent_password": "test_password",
            "concurrent": False,
            "order": 1,
            "options": {"slot": 1}
        }
        add_power_management("test_host", [agent_d])
    """

    for agent in pm_agents:
        if not ll_hosts.add_fence_agent(host_name, **agent):
            return False
    logger.info("Enable power management under host %s", host_name)

    if not ll_hosts.update_host(
        positive=True,
        host=host_name,
        pm=True,
        **kwargs
    ):
        logger.error(
            "Failed to enable power management under host %s", host_name
        )
        return False
    return True


def remove_power_management(host_name):
    """
    Remove all fence agents from host and disable power management

    Args:
        host_name (str): Host name

    Returns:
        bool: True, if remove succeed, otherwise False
    """

    agents = ll_hosts.get_fence_agents_list(host_name)
    for agent in agents:
        if not ll_hosts.remove_fence_agent(agent):
            return False
    logger.info("Disable power management on host %s", host_name)

    if not ll_hosts.update_host(
        positive=True, host=host_name, pm=False
    ):
        logger.error(
            "Cannot disable power management on host: %s" % host_name
        )
        return False
    return True


@ll_general.generate_logs(step=True)
def activate_host_if_not_up(host, host_resource=None):
    """
    Activate the host if the host is not up

    Args:
        host (str): IP/FQDN of the host
        host_resource (VDS): Host resource

    Returns:
        bool: True if host was activated properly False otherwise
    """
    host_status = ll_hosts.get_host_status(host)
    if host_status != ENUMS["host_state_up"]:
        return ll_hosts.activate_host(
            positive=True, host=host, host_resource=host_resource
        )
    return True


def restart_services_under_maintenance_state(
    services, host_resource, timeout=None
):
    """
    1) Put host to maintenance
    2) Restart given services
    3) Activate host
    The services will be restarted by the list order.

    Args:
        services (list): List of services to restart
        host_resource (VDS): host resource
        timeout (int): Timeout for restart service operation

    Returns:
        bool: True, if all actions succeed, otherwise False
    """
    host_name = ll_hosts.get_host_name_from_engine(vds_resource=host_resource)

    if not ll_hosts.deactivate_host(positive=True, host=host_name):
        return False

    service_restarted = False
    logger.info("Restart services %s on %s ", services, host_name)
    for srv in services:
        service_restarted = host_resource.service(srv, timeout).restart()
        if not service_restarted:
            logger.error(
                "Failed to restart service %s, activating host %s",
                srv, host_name
            )
            break
    if not ll_hosts.activate_host(positive=True, host=host_name):
        return False
    return service_restarted


def restart_vdsm_and_wait_for_activation(
    hosts_resource, dc_name, storage_domain_name
):
    """
    1) Restart vdsmd service on service
    2) Wait until storage will be active

    Args:
        hosts_resource (list): Host resources
        dc_name (str): Datacenter name
        storage_domain_name (str): Storage domain name

    Returns:
        bool: True, if all actions succeed, otherwise False
    """
    for host_resource in hosts_resource:
        if not restart_services_under_maintenance_state(
            services=["vdsmd"], host_resource=host_resource
        ):
            return False
    return ll_sd.wait_for_storage_domain_status(
        positive=True,
        data_center_name=dc_name,
        storage_domain_name=storage_domain_name,
        expected_status=ENUMS["storage_domain_state_active"]
    )
